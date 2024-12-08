import datetime
import os
import tempfile
import time
from decimal import Decimal
from threading import Thread
from unittest import mock

import pytest
import requests
import uvicorn
import yaml
from dotenv import load_dotenv

from app.api.client.coinex import CoinexClient
from app.api.coinex import CoinexApi
from app.config.config import read_config_from_yaml
from app.models.order import DbOrder
from tests.fake_exchange.coinex import app, get_exchange

load_dotenv(".env-tests")


class CoinexClientTest(CoinexClient):
    BASE_URL = "http://127.0.0.1:50001/"


@pytest.fixture(scope="session", autouse=True)
def start_test_server():
    """Inicia el servidor FastAPI en un hilo para las pruebas."""

    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=50001, log_level="info")

    # Crear y arrancar el hilo
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()

    # Esperar un momento para asegurarnos de que el servidor arranque
    for _ in range(10):  # Poll for up to 10 seconds
        try:
            response = requests.get(f"{CoinexClientTest.BASE_URL}healthcheck")
            if response.status_code == 200:
                break
        except requests.ConnectionError:
            time.sleep(1)
    else:
        raise RuntimeError("Test server did not start.")
    yield

    # shutdown the fake server
    requests.get(f"{CoinexClientTest.BASE_URL}shutdown")


@pytest.fixture(scope="session", autouse=True)
def create_config():
    data = {
        "binance": {"pairs": {"BTCUSDT": {"amount": 6, "price": 2}}},
        "coinex": {"pairs": {"BTCUSDT": {"amount": 6, "price": 2}}},
    }
    with tempfile.NamedTemporaryFile("w", delete=False) as decimals_temp_file:
        yaml.dump(data, decimals_temp_file)
        decimals_file = decimals_temp_file.name

    with mock.patch("app.config.config.get_decimals_file", return_value=decimals_file):
        with tempfile.NamedTemporaryFile("w", delete=False) as config_temp_file:
            with mock.patch.dict(
                os.environ, {"P_COINEX_BTC1_V2_ACCESS_KEY": "test", "P_COINEX_BTC1_V2_SECRET_KEY": "secret"}
            ):
                valid_data = {
                    "label": "BTC1",
                    "exchange": "coinex",
                    "pair": "BTC/USDT",
                }
                yaml.dump(valid_data, config_temp_file)
                config = read_config_from_yaml(config_temp_file.name)
                yield config

    # Clean up
    for file in [decimals_file, config_temp_file.name]:
        if os.path.exists(file):
            os.remove(file)


@pytest.fixture
def fake_exchange():
    from tests.fake_exchange.coinex import CoinexFakeExchange

    return CoinexFakeExchange(pair="BTC/USDT")


@pytest.fixture
def get_coinex_client():
    client = CoinexClientTest(access_id="test", secret="secret")
    yield client


class TestCoinexClient:
    def test_fake_exchange(self, fake_exchange):
        for i in range(2):
            response = requests.get(
                f"{CoinexClientTest.BASE_URL}spot/deals", params={"market": "BTC/USDT", "limit": 10}
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("data")[0].get("deal_id") == i + 1

    def test_coinex_client_market_deals(self, get_coinex_client):
        data = get_coinex_client.market_deals("BTC/USDT")
        assert data[0].get("deal_id") > 0


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


class TestCoinexApi:
    def test_fetch_price(self, coinex_api):
        price = coinex_api.fetch_price()
        assert price.price > 0
        assert price.date is not None
        assert price.date.tzinfo is not None
        assert price.date.tzinfo == datetime.timezone.utc

    def test_fetch_currency_price(self, coinex_api):
        price = coinex_api.fetch_currency_price("BTC")
        assert price > 0

    def test_get_balance_info(self, coinex_api):
        fake_exchange = get_exchange()
        fake_exchange.add_balance("BTC", Decimal(1))
        balances = coinex_api.get_balances()
        assert len(balances) > 0
        assert balances.get("BTC").available_amount == Decimal(1)

    def test_open_orders(self, coinex_api, db_session):
        fake_exchange = get_exchange()
        fake_exchange.db.add_buy_order("BTC", "0.5", "99000")
        orders = coinex_api.order_pending("BTCUSDT")
        db_orders = db_session.query(DbOrder).all()
        assert len(orders) == 1
        assert len(db_orders) == 1
        assert orders[0].order_id == "1"
        assert db_orders[0].order_id == "1"
