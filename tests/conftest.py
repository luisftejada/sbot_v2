import os
import signal
import time
from decimal import Decimal
from threading import Thread
from unittest import mock

import pytest
import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import create_engine

from app.api.client.coinex import CoinexClient
from app.api.coinex import CoinexApi
from app.config import database
from app.config.config import Config
from app.models.order import Order, OrderStatus, OrderType
from tests.fake_exchange.coinex import SpotOrderRequest
from tests.fake_exchange.models import OrderPendingResponse

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
def coinex_api(get_coinex_client) -> CoinexApi:
    config = create_config()
    coinex_api = CoinexApi(config)
    coinex_api.client = get_coinex_client
    return coinex_api


@pytest.fixture(scope="session", autouse=True)
def get_database_engine():
    load_dotenv("configurations/test/.env-tests")
    CONNECT_URL = os.environ.get("DATABASE_CONNECT")
    DATABASE_NAME = os.environ.get("DATABASE_NAME")
    DATABASE_URL = f"{CONNECT_URL}/{DATABASE_NAME}"
    engine = create_engine(DATABASE_URL)
    database.set_engine(engine)
    with mock.patch.object(database, "get_engine", return_value=engine):
        yield engine


@pytest.fixture
def db_session(get_database_engine):
    from sqlalchemy.orm import sessionmaker

    from app.config.database import Base

    engine = get_database_engine
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
    exchange = get_exchange()
    yield exchange
    exchange.reset()


def get_exchange():
    from tests.fake_exchange.coinex import CoinexFakeExchange

    exchange = CoinexFakeExchange()
    if exchange.config is None:
        config = create_config()
        exchange.set_config(config)
    exchange.db.set_config(exchange.config)
    return exchange


# def reset_exchange():
#     global _exchange
#     _exchange = None


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
async def limit_order(order_request: SpotOrderRequest):
    print(f"Creating order: {order_request}")
    exchange = get_exchange()
    order = Order(
        order_id=exchange.db.next_order_id,
        created=exchange._get_current_date(),
        executed=None,
        type=order_request.side,
        buy_price=Decimal(order_request.price) if order_request.side == OrderType.BUY.value else None,
        sell_price=Decimal(order_request.price) if order_request.side == OrderType.SELL.value else None,
        status=OrderStatus.INITIAL,
        amount=Decimal(order_request.amount),
        filled=None,
        benefit=None,
        market=order_request.market,
        market_type=order_request.market_type,
    )
    if order.type == OrderType.BUY:
        return exchange.add_buy_order(order).model_dump()
    else:
        return {}
        # TODO: return exchange.add_sell_order(order).model_dump()


@app.get("/spot/pending-order")
async def order_pending(market: str, page: int = 1, limit: int = 100):
    exchange = get_exchange()
    exchange_orders = exchange.db.open_orders
    return OrderPendingResponse.from_orders(exchange_orders).model_dump()


@app.get("/spot/user-deals")
async def user_deals(market: str, side: str, page: int = 1, limit: int = 100):
    exchange = get_exchange()
    return {
        "code": 0,
        "data": [exchange.db.as_coinex_order(order) for order in exchange.db.completed_orders],
        "pagination": {"total": 1, "has_next": False},
        "message": "OK",
    }
