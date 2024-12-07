from decimal import Decimal
from typing import Dict, List

from tests.fake_exchange.models import Balance, Order, OrderStatus, OrderType

_db = None


class Db:
    balances: Dict[str, Balance] = {}
    open_orders: List[Order] = []
    completed_orders: List[Order] = []

    def get_balance(self, currency: str) -> Balance:
        return self.balances.get(currency)

    def increase_balance(self, currency: str, amount: Decimal):
        balance = self.balances.get(currency)
        if balance is None:
            balance = Balance(currency=currency)
            self.balances[currency] = balance
        balance.available_amount += amount

    def add_order(self, order: Order):
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


def get_db():
    global _db
    if _db is None:
        _db = Db()
    return _db
