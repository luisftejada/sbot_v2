import random
from decimal import Decimal
from typing import Dict, List

from app.common.common import singleton
from app.config.config import Config
from app.models.order import Order, OrderStatus, OrderType
from tests.fake_exchange.models import Balance


@singleton
class Db:
    def __init__(self, pair: str = "BTC/USDT"):
        self.order_id = 1
        self.fill_id = 1
        self.pair = pair
        self.balances: Dict[str, Balance] = {}
        self.open_orders: List[Order] = []
        self.completed_orders: List[Order] = []
        self.config: Config | None = None

    def reset(self):
        self.order_id = 1
        self.balances = {}
        self.open_orders = []
        self.completed_orders = []
        self.config = None
        self.fill_id = 1

    def set_config(self, config: Config):
        self.config = config

    @property
    def next_order_id(self) -> str:
        self.order_id += 1
        return str(self.order_id - 1)

    def set_pair(self, pair: str):
        self.pair = pair

    @property
    def market(self):
        return self.pair.replace("/", "")

    def get_balance(self, currency: str) -> Balance:
        return self.balances.get(currency)

    def get_balances(self):
        return self.balances.values()

    def increase_balance(self, currency: str, amount: Decimal):
        balance = self.balances.get(currency)
        if balance is None:
            balance = Balance(currency=currency)
            self.balances[currency] = balance
        balance.available_amount += amount

    def _get_balances(self, order: Order) -> List[Balance]:
        return [self.get_balance(order.currency_from()), self.get_balance(order.currency_to())]

    def add_buy_order(self, buy_order: Order):
        balance_from, balance_to = self._get_balances(buy_order)
        if balance_to is None:
            raise Exception(f"Balance not found. order={buy_order.model_dump()}")
        if balance_to.available_amount < self.config.rnd_amount_by_ccy(
            buy_order.amount * buy_order.buy_price, buy_order.currency_to()
        ):
            raise Exception(f"Not enough balance. order={buy_order.model_dump()}, balance={balance_to.model_dump()}")
        balance_to.lock(self.config.rnd_amount_by_ccy(buy_order.amount * buy_order.buy_price, buy_order.currency_to()))
        self._add_order(buy_order)

    def add_sell_order(self, sell_order: Order):
        balance_from, balance_to = self._get_balances(sell_order)
        if balance_from is None:
            raise Exception(f"Balance not found. order={sell_order.model_dump()}")
        if balance_from.available_amount < self.config.rnd_amount_by_ccy(sell_order.amount, sell_order.currency_from()):
            raise Exception(f"Not enough balance. order={sell_order.model_dump()}, balance={balance_from.model_dump()}")
        balance_from.lock(self.config.rnd_amount_by_ccy(sell_order.amount, sell_order.currency_from()))
        self._add_order(sell_order)

    def _add_order(self, order: Order):
        self.open_orders.append(order)

    def create_buy_order(self, market: str, amount: Decimal, price: Decimal):
        self.add_order(Order(market=market, type=OrderType.BUY, amount=amount, status=OrderStatus.OPEN, price=price))

    def create_sell_order(self, market: str, amount: Decimal, price: Decimal):
        self.add_order(Order(market=market, type=OrderType.SELL, amount=amount, status=OrderStatus.OPEN, price=price))

    def cancel_order(self, order_id: str):
        for order in self.open_orders:
            if order.order_id == order_id:
                if order.type == OrderType.BUY:
                    balance_from, balance_to = self._get_balances(order)
                    balance_to.unlock(
                        self.config.rnd_amount_by_ccy(order.amount * order.buy_price, order.currency_to())
                    )
                else:  # OrderType.SELL
                    balance_from, balance_to = self._get_balances(order)
                    balance_from.unlock(self.config.rnd_amount_by_ccy(order.amount, order.currency_from()))
                self.open_orders.remove(order)
                return order
        raise Exception(f"Order not found: {order_id}")

    def check_buy_orders(self, market: str, price: Decimal):
        any_completed = False
        for order in self.open_orders:
            if order.market == market and order.type == OrderType.BUY and price <= order.buy_price:
                order.orderStatus = OrderStatus.EXECUTED
                balance_from, balance_to = self._get_balances(order)
                balance_to.unlock(self.config.rnd_amount_by_ccy(order.amount * order.buy_price, order.currency_to()))
                balance_to.dec(self.config.rnd_amount_by_ccy(order.amount * order.buy_price, order.currency_to()))
                balance_from.inc(self.config.rnd_amount(order.amount))
                any_completed = True
        if any_completed:
            self.update_completed_orders(OrderType.BUY)

    def check_sell_orders(self, market: str, price: Decimal):
        any_completed = False
        for order in self.open_orders:
            if order.market == market and order.type == OrderType.SELL and price >= order.sell_price:
                order.orderStatus = OrderStatus.EXECUTED

                balance_from = self.get_balance(order.currency_from())
                balance_from.dec(order.amount)
                balance_to = self.get_balance(order.currency_to())
                balance_to.inc(order.amount * order.sell_price)
                any_completed = True
        if any_completed:
            self.update_completed_orders(OrderType.SELL)

    def update_completed_orders(self, side: OrderStatus) -> List[Order]:
        completed = [
            order for order in self.open_orders if order.orderStatus == OrderStatus.EXECUTED and order.type == side
        ]
        self.completed_orders.extend(completed)
        self.open_orders = [order for order in self.open_orders if order.orderStatus != OrderStatus.EXECUTED]
        return completed

    def as_coinex_order(self, order: Order) -> dict[str, str]:
        return {
            "order_id": int(order.order_id),
            "market": self.market,
            "market_type": "SPOT",
            "type": "limit",
            "side": order.type.value,
            "amount": str(order.amount),
            "price": str(order.buy_price) if order.type == OrderType.BUY else str(order.sell_price),
            "created_at": order.created.timestamp() * 1000,
        }

    def fills_from_completed_order(self, order: Order) -> list[dict[str, str]]:
        fills = []
        splits = random.choice([1, 2, 3])
        base_amount = order.amount / splits
        accumulated_amount = Decimal(0)
        for split in range(splits):
            fill_amount = self.config.rnd_amount(base_amount)
            if split == splits - 1:
                fill_amount = order.amount - accumulated_amount
            accumulated_amount += fill_amount
            fill = {
                "deal_id": self.fill_id,
                "order_id": int(order.order_id),
                "market": self.market,
                "price": str(order.buy_price) if order.type == OrderType.BUY else str(order.sell_price),
                "amount": str(fill_amount),
                "side": order.type.value,
                "created_at": order.created.timestamp() * 1000,
            }
            self.fill_id += 1
            fills.append(fill)
        return fills


def get_db(reset=False):
    if reset:
        db = Db()
        db.reset()
        return db
    else:
        return Db()
