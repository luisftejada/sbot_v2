import datetime
from decimal import Decimal
from typing import Dict, List

from app.models.order import Order, OrderStatus, OrderType
from tests.fake_exchange.models import Balance

_db = None


class Db:
    balances: Dict[str, Balance] = {}
    open_orders: List[Order] = []
    completed_orders: List[Order] = []

    def __init__(self, pair: str = "BTC/USDT"):
        self.order_id = 1
        self.pair = pair

    @property
    def next_order_id(self) -> str:
        self.order_id += 1
        return str(self.order_id - 1)

    def set_pair(self, pair: str):
        self.pair = pair

    @property
    def symbol(self):
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

    def add_buy_order(self, currency: str, amount: str, price: str, date: datetime.datetime | None = None):
        buy_order = Order(
            order_id=str(self.order_id),
            created=date or datetime.datetime.now(tz=datetime.UTC),
            executed=None,
            type=OrderType.BUY,
            buy_price=Decimal(price),
            sell_price=None,
            status=OrderStatus.INITIAL,
            amount=Decimal(amount),
            filled=None,
            benefit=None,
        )
        self.order_id += 1
        self._add_order(buy_order)

    def _add_order(self, order: Order):
        self.open_orders.append(order)

    def create_buy_order(self, symbol: str, amount: Decimal, price: Decimal):
        self.add_order(Order(pair=symbol, type=OrderType.BUY, amount=amount, status=OrderStatus.OPEN, price=price))

    def create_sell_order(self, symbol: str, amount: Decimal, price: Decimal):
        self.add_order(Order(pair=symbol, type=OrderType.SELL, amount=amount, status=OrderStatus.OPEN, price=price))

    def check_buy_orders(self, symbol: str, price: Decimal):
        for order in self.open_orders:
            if order.pair == symbol and order.type == OrderType.BUY and price <= order.price:
                order.status = OrderStatus.COMPLETED

                balance_from = self.get_balance(symbol.split("/")[0])
                balance_from.inc(order.amount)
                balance_to = self.get_balance(symbol.split("/")[1])
                balance_to.dec(order.amount * order.price)

    def check_sell_orders(self, symbol: str, price: Decimal):
        for order in self.open_orders:
            if order.pair == symbol and order.type == OrderType.SELL and price >= order.price:
                order.status = OrderStatus.COMPLETED

                balance_from = self.get_balance(symbol.split("/")[0])
                balance_from.dec(order.amount)
                balance_to = self.get_balance(symbol.split("/")[1])
                balance_to.inc(order.amount * order.price)

    def get_completed_orders(self) -> List[Order]:
        completed = [order for order in self.open_orders if order.status == OrderStatus.COMPLETED]
        self.completed_orders.extend(completed)
        self.open_orders = [order for order in self.open_orders if order.status != OrderStatus.COMPLETED]
        return completed

    def as_coinex_order(self, order: Order) -> dict[str, str]:
        return {
            "order_id": int(order.order_id),
            "market": self.symbol,
            "market_type": "SPOT",
            "type": "limit",
            "side": order.type.value,
            "amount": str(order.amount),
            "price": str(order.buy_price) if order.type == OrderType.BUY else str(order.sell_price),
            "created_at": order.created.timestamp() * 1000,
        }


def get_db(reset=False):
    global _db
    if _db is None or reset is True:
        _db = Db()
    return _db
