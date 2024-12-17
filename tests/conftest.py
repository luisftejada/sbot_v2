import os
import signal
import time
from threading import Thread
from unittest import mock

import pytest
import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.client.coinex import CoinexClient
from app.api.coinex import CoinexApi
from app.config.config import Config
from app.models.order import Order, OrderStatus, OrderType
from tests.fake_exchange.coinex import SpotOrderRequest

load_dotenv("configurations/test/.env-tests")

app = FastAPI()


class CoinexClientTest(CoinexClient):
    BASE_URL = "http://127.0.0.1:50001/"


def create_config():
    config_file_path = os.environ["CONFIG_FILE"]
    with mock.patch.dict(os.environ, {"P_COINEX_BTC1_V2_ACCESS_KEY": "test", "P_COINEX_BTC1_V2_SECRET_KEY": "secret"}):
        config = Config.read_config_from_yaml(config_file_path)
        return config


@pytest.fixture
def coinex_api(create_config, get_coinex_client) -> CoinexApi:
    config = create_config
    coinex_api = CoinexApi(config)
    coinex_api.client = get_coinex_client
    return coinex_api


@pytest.fixture
def db_session():
    CONNECT_URL = os.environ.get("DATABASE_CONNECT")
    DATABASE_NAME = os.environ.get("DATABASE_NAME")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config.database import Base

    DATABASE_URL = f"{CONNECT_URL}/{DATABASE_NAME}"
    engine = create_engine(DATABASE_URL)
    print(DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    # Teardown
    session.close()
    # Base.metadata.drop_all(bind=engine)


@pytest.fixture
def fake_exchange():
    yield get_fake_exchange()

    reset_exchange()


def get_fake_exchange() -> "CoinexFakeExchange":  # noqa: F821
    from tests.fake_exchange.coinex import CoinexFakeExchange

    exchange = CoinexFakeExchange()
    config = create_config()
    exchange.set_config(config)
    return exchange


_exchange = None


def get_exchange():
    global _exchange
    if _exchange is None:
        _exchange = get_fake_exchange()
    return _exchange


def reset_exchange():
    global _exchange
    _exchange = None


@pytest.fixture
def get_coinex_client():
    client = CoinexClientTest(access_id="test", secret="secret")
    yield client


@pytest.fixture(scope="session", autouse=True)
def start_test_server():
    """Inicia el servidor FastAPI en un hilo para las pruebas."""

    def run_server():
        exchange = get_exchange()  # noqa: F841
        uvicorn.run(app, host="127.0.0.1", port=50001, log_level="info")

    # Crear y arrancar el hilo
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1)
    yield

    # shutdown the fake server
    requests.get(f"{CoinexClientTest.BASE_URL}shutdown")
    reset_exchange()


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
