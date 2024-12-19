"""
This is a fake exchange module for testing purposes.
"""
import datetime
import os
from decimal import Decimal

from dotenv import load_dotenv
from pydantic import BaseModel

from app.common.common import singleton
from app.config.config import Config
from app.models.order import DbOrder, Order
from app.models.price import Price
from tests.fake_exchange.db import Db
from tests.fake_exchange.models import BuyOrderResponse

load_dotenv("configurations/test/.env-tests")


class CoinexOrder(Order):
    market: str
    market_type: str

    def get_coinex_data(self):
        return {
            "order_id": self.order_id,
            "market": self.market,
            "market_type": self.market_type,
            "side": self.type.value,
            "ccy": self.market.split("/")[0],
            "amount": f"{self.amount:.8f}",
        }


class StopLongRun(Exception):
    pass


@singleton
class CoinexFakeExchange:
    def __init__(self):
        self.db = Db()
        self.prices = []
        self.index = 0
        self.config = None
        self.prices = []
        self.prices_folder = None
        self.current_file_index = 0
        self.prices_folder = os.environ.get("DATAPATH")
        if not os.path.exists(self.prices_folder):
            raise RuntimeError("can't find DATAPATH = {prices_folder}")
        self.previous_price = None

        self.data_files = sorted(os.listdir(self.prices_folder))
        if len(self.data_files) == 0:
            raise RuntimeError("no data files found in {prices_folder}")

    def set_config(self, config: Config):
        self.config = config
        self.market = config.market
        self.load_file_of_prices()
        self.db.set_config(config)

    @property
    def current_file(self):
        return os.path.join(self.prices_folder, self.data_files[self.current_file_index])

    def reset(self, db_session=None, clean_db=False):
        self.db.reset()
        self.prices = []
        self.index = 0
        self.current_file_index = 0
        self.previous_price = None
        self.load_file_of_prices()
        if clean_db:
            assert db_session is not None
            for db_class in [DbOrder]:
                self._clean_db_class(db_session, db_class)

    def _clean_db_class(self, db_session, db_class):
        db_session.query(db_class).delete()
        db_session.commit()

    def load_file_of_prices(self):
        print(f"loading prices from {self.current_file}")
        with open(self.current_file, "r") as file:
            self.prices = [line.split(",") for line in file.readlines()]

    def upload_manual_prices(self, prices: list[list[str]]):
        self.prices = prices

    def _get_current_date(self) -> datetime.datetime:
        line = self.prices[self.index]
        return datetime.datetime.fromisoformat(line[0])

    def get_current_price(self) -> Price:
        if len(self.prices) == 0:
            self.load_file_of_prices()
            self.index = 0
        elif self.index >= len(self.prices):
            self.index = 0
            if self.current_file <= len(self.data_files):
                self.current_file += 1
            else:
                raise StopLongRun()
            self.load_file_of_prices()

        line = self.prices[self.index]
        new_price = False
        while not new_price or (self.previous_price and self.previous_price.price == new_price.price):
            try:
                new_price = Price(price=Decimal(line[1]), date=datetime.datetime.fromisoformat(line[0]))
            except Exception:
                pass
            self.index += 1
            line = self.prices[self.index]

        self.previous_price = new_price
        self.db.check_buy_orders(self.market, new_price.price)
        self.db.check_sell_orders(self.market, new_price.price)
        return new_price

    def add_balance(self, currency: str, amount: Decimal):
        self.db.increase_balance(currency=currency, amount=amount)

    def add_buy_order(self, order: Order) -> BuyOrderResponse:
        self.db.add_buy_order(buy_order=order)
        response = BuyOrderResponse.from_order(order=order)
        return response

    def get_open_orders(self):
        return self.db.open_orders


class UnkonwnMarketException(Exception):
    pass


class SpotOrderRequest(BaseModel):
    market: str
    market_type: str
    side: str
    type: str
    price: Decimal
    amount: Decimal

    @property
    def pair(self) -> str:
        for currency in ["USDT", "BTC", "USDC"]:
            if currency in self.market:
                return f"{self.market.replace(currency, " ")}/{currency}"

        raise UnkonwnMarketException(f"Unknown market {self.market}")
