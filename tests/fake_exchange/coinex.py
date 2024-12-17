"""
This is a fake exchange module for testing purposes.
"""
import datetime
import os
import signal
from decimal import Decimal

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from app.config.config import Config
from app.models.order import Order, OrderStatus, OrderType
from app.models.price import Price
from tests.fake_exchange.db import Db, get_db
from tests.fixtures import get_exchange

load_dotenv("configurations/test/.env-tests")
app = FastAPI()


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


class CoinexFakeExchange:
    def __init__(self):
        self.db: Db = get_db(reset=True)
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
        self.pair = config.pair
        self.load_file_of_prices()

    @property
    def current_file(self):
        return os.path.join(self.prices_folder, self.data_files[self.current_file_index])

    def load_file_of_prices(self):
        print(f"loading prices from {self.current_file}")
        with open(self.current_file, "r") as file:
            self.prices = [line.split(",") for line in file.readlines()]

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
        return new_price

    def add_balance(self, currency: str, amount: Decimal):
        self.db.increase_balance(currency=currency, amount=amount)

    def add_order(self, order: Order):
        self.db.add_order(order)


@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}


@app.get("/shutdown")
async def shutdown():
    os.kill(os.getpid(), signal.SIGINT)


@app.get("/spot/deals")
async def market_deals():
    exchange = get_exchange()
    price = exchange.get_current_price()
    return {
        "code": 0,
        "data": [
            {
                "deal_id": exchange.index,
                "created_at": int(price.date.timestamp() * 1000),
                "price": f"{price.price: .2f}",
                "amount": "1.0",
            }
        ],
    }


@app.get("/assets/spot/balance")
async def balance_info():
    exchange = get_exchange()
    data = []
    for balance in exchange.db.get_balances():
        data.append(balance.get_coinex_data())
    return {"code": 0, "data": data, "message": "OK"}


@app.get("/spot/pending-order")
async def get_pending_orders():
    exchange = get_exchange()
    orders = exchange.db.open_orders
    return {
        "code": 0,
        "data": [exchange.db.as_coinex_order(order) for order in orders],
        "pagination": {"total": 1, "has_next": False},
        "message": "OK",
    }


class SpotOrderRequest(BaseModel):
    market: str
    market_type: str
    side: OrderType
    price: Decimal
    amount: Decimal
    created: datetime.datetime
    type: str


@app.post("/spot/order")
async def limit_order(order: SpotOrderRequest):
    exchange = get_exchange()
    order = Order(
        order_id=exchange.db.next_order_id,
        created=order.created,
        executed=None,
        type=order.side,
        buy_price=order.price if order.side == OrderType.BUY else None,
        sell_price=order.price if order.side == OrderType.SELL else None,
        status=OrderStatus.INITIAL,
        amount=order.amount,
        filled=None,
        benefit=None,
        market=order.market,
        market_type=order.market_type,
    )
    exchange.add_order(order)
    return {"code": 0, "data": order.get_coinex_data(), "message": "OK"}
