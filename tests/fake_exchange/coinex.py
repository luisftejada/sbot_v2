"""
This is a fake exchange module for testing purposes.
"""
import datetime
import os
import signal
from decimal import Decimal

from fastapi import FastAPI

from app.models.price import Price
from tests.fake_exchange.db import get_db

app = FastAPI()


class CoinexFakeExchange:
    def __init__(self, pair: str, prices_file_path: str = None):  # e.g., "BTC/USDT"
        self.db = get_db()
        self.prices_file_path = prices_file_path
        self.pair = pair
        self.prices = self.load_prices()
        self.index = 0

    def load_prices(self):
        if self.prices_file_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_name = f"data/{self.pair.replace('/', '_')}.txt"
            full_path = os.path.join(base_dir, file_name)
        else:
            full_path = self.prices_file_path
        prices = []
        with open(full_path) as f:
            for line in f.readlines():
                date = datetime.datetime.fromisoformat(line.split(",")[0])
                date.replace(tzinfo=datetime.timezone.utc)
                price = Decimal(line.split(",")[1])
                prices.append(Price(date=date, price=price))

        return prices


_exchange = None


def get_exchange():
    global _exchange
    if _exchange is None:
        _exchange = CoinexFakeExchange(pair="BTC/USDT")
    return _exchange


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
