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

from app.api.client.coinex import CoinexClient
from app.api.coinex import CoinexApi
from app.config.config import Config
from app.models.enums import OrderStatus, OrderType
from app.models.filled import DbFill
from app.models.order import DbExecuted, Order
from tests.fake_exchange.coinex import (
    SpotCancelOrderRequest,
    SpotLimitOrderRequest,
    SpotMarketOrderRequest,
)
from tests.fake_exchange.models import OrderPendingResponse

load_dotenv("configurations/test/.env-tests")

app = FastAPI()


class CoinexClientTest(CoinexClient):
    BASE_URL = "http://127.0.0.1:50001/"


def create_config():
    config_file_path = os.environ["CONFIG_FILE"]
    with mock.patch.dict(os.environ, {"P_COINEX_ADA1_V2_ACCESS_KEY": "test", "P_COINEX_ADA1_V2_SECRET_KEY": "secret"}):
        config = Config.read_config_from_yaml(config_file_path)
        return config


@pytest.fixture(autouse=True)
def new_tables():
    for _cls in [Order, DbFill, DbExecuted]:
        _cls.delete_table("ADA1")
        _cls.create_table("ADA1")
    yield
    for _cls in [Order, DbFill, DbExecuted]:
        _cls.delete_table("ADA1")


@pytest.fixture
def coinex_api(get_coinex_client) -> CoinexApi:
    config = create_config()
    coinex_api = CoinexApi(config)
    coinex_api.client = get_coinex_client
    return coinex_api


@pytest.fixture
def fake_exchange():
    exchange = get_exchange()
    yield exchange
    exchange.reset()


def get_exchange(reset: bool = False):
    from tests.fake_exchange.coinex import CoinexFakeExchange

    exchange = CoinexFakeExchange()
    if exchange.config is None:
        config = create_config()
        exchange.set_config(config)
    exchange.db.set_config(exchange.config)
    if reset:
        exchange.reset()
    return exchange


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


@app.get("/spot/pending-order")
async def order_pending(market: str, page: int = 1, limit: int = 100):
    exchange = get_exchange()
    exchange_orders = exchange.db.open_orders
    return OrderPendingResponse.from_orders(exchange_orders).model_dump()


@app.get("/spot/user-deals")
async def user_deals(market: str, market_type: str = "SPOT", limit: int = 100, start_time: int = 0):
    exchange = get_exchange()
    fills = []
    for completed_order in exchange.db.completed_orders:
        fills += exchange.db.fills_from_completed_order(completed_order)

    return {
        "code": 0,
        "data": fills,
        "pagination": {"total": 1, "has_next": False},
        "message": "OK",
    }


@app.post("/spot/order")
async def limit_order(order_request: SpotLimitOrderRequest | SpotMarketOrderRequest):
    print(f"Creating order: {order_request}")
    exchange = get_exchange()
    match order_request.type:
        case "market":
            price = exchange.get_current_price().price
        case "limit":
            price = order_request.price
        case _:
            raise RuntimeError(f"Error creating order: {order_request}")

    order = Order(
        order_id=exchange.db.next_order_id,
        created=exchange._get_current_date(),
        executed=None,
        type=order_request.side,
        buy_price=Decimal(price) if order_request.side == OrderType.BUY.value else None,
        sell_price=Decimal(price) if order_request.side == OrderType.SELL.value else None,
        orderStatus=OrderStatus.INITIAL,
        amount=Decimal(order_request.amount),
        fills=[],
        benefit=None,
        market=order_request.market,
        market_type=order_request.market_type,
    )
    match order_request.type:
        case "market":
            return exchange.add_market_order(order).model_dump()
        case "limit":
            match order.type:
                case OrderType.BUY:
                    return exchange.add_buy_order(order).model_dump()
                case OrderType.SELL:
                    return exchange.add_sell_order(order).model_dump()
                case _:
                    raise RuntimeError(f"Error creating limit order: Invalid order type: {order.type}")
        case _:
            raise RuntimeError(f"Error creating order: Invalid request: {order_request}")


@app.post("/spot/cancel-order")
async def cancel_order(cance_order_request: SpotCancelOrderRequest):
    exchange = get_exchange()
    cancelled_order = exchange.cancel_order(cance_order_request.order_id)
    return cancelled_order.model_dump()
