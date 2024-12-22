import datetime
from decimal import Decimal
from typing import Optional

from app.api.base import BaseApi
from app.api.client.binance import BinanceClient
from app.models.balance import Balance
from app.models.enums import OrderType
from app.models.filled import Fill
from app.models.order import Order
from app.models.price import Price

NullPrice = Price(date=datetime.datetime.now(datetime.timezone.utc), price=0)


class BinanceApi(BaseApi):
    def __init__(self, config):
        super().__init__(config)
        self.client = BinanceClient(config)

    def get_client(self):
        return None

    def fetch_price(self) -> Price:
        return NullPrice

    def fetch_currency_price(self, currency) -> Decimal:
        return Decimal(0)

    def get_balances(self) -> dict[str, Balance]:
        return {}

    def order_pending(self, market: str, page: int = 1, limit: int = 100, **params):
        pass

    def create_buy_order(self, market: str, amount: Decimal, price: Decimal) -> Order:
        return Order()

    def create_sell_order(self, market: str, amount: Decimal, price: Decimal) -> Order:
        return Order()

    def cancel_order(self, market: str, order_id) -> Order:
        return Order()

    def get_filled(self, side: OrderType, fill: Fill | None, pair: Optional[str] = None) -> list[Fill]:
        return []
