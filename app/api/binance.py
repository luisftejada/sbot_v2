import datetime

from app.api.base import BaseApi
from app.api.client.binance import BinanceClient
from app.models.price import Price


class BinanceApi(BaseApi):
    def __init__(self, config):
        super().__init__(config)
        self.client = BinanceClient(config)

    def get_client(self):
        return None

    def fetch_price(self) -> Price:
        return Price(date=datetime.datetime.now(datetime.timezone.utc), price=0)

    def create_buy_order(self, symbol, amount, price):
        pass
