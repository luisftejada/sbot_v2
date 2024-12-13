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


class CoinexFakeExchange:
    def __init__(self):
        self.db: Db = get_db(reset=True)
        self.prices = []
        self.index = 0
        self.config = None
        self.prices = []

    def set_config(self, config: Config):
        self.config = config
        self.pair = config.pair
        self.prices = self.load_prices()

    def load_prices(self):
        prices_folder = os.environ.get("DATAPATH")
        if not os.path.exists(prices_folder):
            raise RuntimeError("can't find DATAPATH = {prices_folder}")

        self.data_files = sorted(os.listdir(prices_folder))
        self.current_file = self.data_files[0]

    def load_file_of_prices(self):
        with open(self.current_file, "r") as file:
            self.prices = [line.split(",") for line in file.readlines()]

    def get_current_price(self) -> Price:
        if len(self.prices) == 0:
            self.load_file_of_prices()
            self.index = 0

        line = self.prices[self.index]
        new_price = False
        while not new_price:
            try:
                new_price = Price(price=Decimal(line[1]), date=datetime.datetime.fromisoformat(line[0]))
            except Exception:
                self.index += 1
                line = self.prices[self.index]
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
    if exchange.index >= len(exchange.prices):
        exchange.index = 0
    price = exchange.prices[exchange.index]
    exchange.index += 1
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
