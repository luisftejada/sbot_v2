import datetime
from decimal import Decimal
from typing import Optional

from app.api.base import BaseApi
from app.api.client.coinex import CoinexClient
from app.config.config import Config
from app.models.balance import Balance
from app.models.enums import MarketOrderType, OrderType
from app.models.filled import DbFill, Fill
from app.models.order import Executed, Order, OrderTypeError
from app.models.price import Price


class FetchBalanceException(RuntimeError):
    def __init__(self):
        self.error = "error fetching balance"
        self.payload = {}


class CoinexApi(BaseApi):
    def __init__(self, config: Config):
        super().__init__(config)
        self.client = CoinexClient(config)
        self.previous_price: Decimal | None = None
        self.config = config
        self.last_fill = DbFill.get(self.bot_name, self.bot_name)

    @property
    def bot_name(self):
        return self.config.label

    def get_client(self):
        return CoinexClient(self.config.client.key, self.config.client.secret)

    def fetch_price(self) -> Price:
        price = self.previous_price
        while price == self.previous_price:
            deals = self._execute(self.client.market_deals, self.config.market, limit=1, rate=Decimal(1))
            if deals:
                price = self.config.rnd_price(Decimal(deals[0].get("price")))
        self.previous_price = price
        new_price = Price(date=datetime.datetime.now(datetime.timezone.utc), price=price)
        return new_price

    def fetch_currency_price(self, currency) -> Decimal:
        deals = self._execute(self.client.market_deals, f"{currency}USDT", limit=1, rate=Decimal(1))
        if deals:
            return self.config.rnd_price(Decimal(deals[0].get("price")))
        else:
            return Decimal("0")

    def get_balances(self) -> dict[str, Balance]:
        return_balances = {}
        balances = self._execute(self.client.balance_info)
        if balances is None:
            raise FetchBalanceException()

        for currency in self.config.currencies:
            if currency not in balances:
                return_balances[currency] = Balance(
                    currency=currency, available=Decimal(0), locked_amount=Decimal(0), rinconcito_usdt=Decimal(0)
                )
            else:
                bal = balances.get(currency)
                return_balances[currency] = Balance.create_from_coinex(currency=currency, data=bal, config=self.config)
        return return_balances

    def order_pending(self, market: str, page: int = 1, limit: int = 100, **params):
        exchange_orders = self._execute(self.client.order_pending, self.config.market)
        if exchange_orders is None:
            return []

        orders = []
        for order in exchange_orders:
            new_order = Order.create_from_coinex(self.config, order)
            try:
                found = Order.get(self.bot_name, new_order.order_id)
                orders.append(found)
            except Order.NotFoundError:
                Order.save(self.bot_name, new_order)
                orders.append(new_order)
        return orders

    def _create_order(
        self, market: str, amount: Decimal, buy_price: Decimal, side: OrderType, sell_price: Optional[Decimal] = None
    ) -> Order:
        am = self.config.rnd_amount(amount, cls=float)
        match side:
            case side.BUY:
                pr = self.config.rnd_price(buy_price, cls=float)
            case side.SELL:
                pr = self.config.rnd_price(sell_price, cls=float)
            case _:
                raise OrderTypeError(side)

        created = self._execute(self.client.order_limit, market, side.value, am, pr)
        new_order = Order.create_from_coinex(self.config, created)
        if side == OrderType.SELL:
            new_order.buy_price = Decimal(buy_price)
        Order.save(self.bot_name, new_order)
        return new_order

    def create_buy_order(self, market: str, amount: Decimal, price: Decimal) -> Order:
        return self._create_order(market=market, amount=amount, buy_price=price, side=OrderType.BUY)

    def create_sell_order(self, market: str, amount: Decimal, buy_price: Decimal, sell_price: Decimal) -> Order:
        return self._create_order(
            market=market, amount=amount, buy_price=buy_price, sell_price=sell_price, side=OrderType.SELL
        )

    def create_market_order(self, market: str, amount: Decimal, order_type: MarketOrderType) -> Order:
        am = self.config.rnd_amount(amount, cls=float)
        created = self._execute(self.client.order_market, market, order_type.side.value, am)
        new_order = Order.create_from_coinex(self.config, created)
        executed = Executed.load_day(bot=self.bot_name, day=new_order.executed_day())
        executed.add_executed_order(new_order, order_type)
        executed.save()
        return new_order

    def cancel_order(self, market: str, order_id: str) -> Order:
        cancelled = self._execute(self.client.order_pending_cancel, market=market, id=order_id)
        if cancelled:
            Order.delete(self.bot_name, order_id)
        else:
            raise Exception(f"Error cancelling order: {order_id}")
        return cancelled

    def get_filled(self, side: OrderType, fill: Fill | None, pair: Optional[str] = None) -> list[Fill]:
        match side:
            case OrderType.BUY:
                date_from = fill.buy_date if fill and fill.buy_date else datetime.datetime(2024, 1, 1)
            case OrderType.SELL:
                date_from = fill.sell_date if fill and fill.sell_date else datetime.datetime(2024, 1, 1)

        start_time = int(date_from.timestamp())
        fills = self._execute(self.client.order_user_deals, self.config.market, start_time=start_time)
        _fills = [Fill.from_coinex(fill) for fill in fills if fill.get("side") == side.value]
        return _fills

    def join_orders(self, market: str, price: Price, order1: Order, order2: Order) -> Order:
        self.cancel_order(market, order1.order_id)
        self.cancel_order(market, order2.order_id)
        order1.buy_price = order1.buy_price or price.price
        order2.buy_price = order2.buy_price or price.price
        order1.sell_price = order1.sell_price or price.price
        order2.sell_price = order2.sell_price or price.price
        new_amount = order1.amount + order2.amount
        new_buy_price = self.config.rnd_price(
            (order1.amount * order1.buy_price + order2.amount * order2.buy_price) / new_amount
        )
        new_sell_price = self.config.rnd_price(
            (order1.amount * order1.sell_price + order2.amount * order2.sell_price) / new_amount
        )

        new_order = self.create_sell_order(
            market=market, amount=new_amount, buy_price=new_buy_price, sell_price=new_sell_price
        )
        return new_order
