import datetime
from decimal import Decimal
from typing import Optional

from app.api.base import BaseApi
from app.api.client.coinex import CoinexClient
from app.config.config import Config
from app.models.balance import Balance
from app.models.enums import OrderType
from app.models.filled import DbFill, Fill
from app.models.order import Order
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
                return_balances[currency] = Balance(currency=currency, total=Decimal(0), locked=Decimal(0))
            else:
                bal = balances.get(currency)
                return_balances[currency] = Balance(
                    currency=currency,
                    available_amount=Decimal(bal.get("available")) + Decimal(bal.get("frozen")),
                    locked_amount=Decimal(bal.get("frozen")),
                )
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

    def _create_order(self, market: str, amount: Decimal, price: Decimal, side: OrderType) -> Order:
        am = self.config.rnd_amount(amount, cls=float)
        pr = self.config.rnd_price(price, cls=float)
        created = self._execute(self.client.order_limit, market, side.value, am, pr)
        new_order = Order.create_from_coinex(self.config, created)
        Order.save(self.bot_name, new_order)
        return new_order

    def create_buy_order(self, market: str, amount: Decimal, price: Decimal) -> Order:
        return self._create_order(market=market, amount=amount, price=price, side=OrderType.BUY)

    def create_sell_order(self, market: str, amount: Decimal, price: Decimal) -> Order:
        return self._create_order(market=market, amount=amount, price=price, side=OrderType.SELL)

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
