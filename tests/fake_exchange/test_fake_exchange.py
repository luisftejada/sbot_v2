import time
from threading import Thread

import pytest
import requests
import uvicorn

from app.api.client.coinex import CoinexClient
from tests.fake_exchange.coinex import app


class CoinexClientTest(CoinexClient):
    BASE_URL = "http://127.0.0.1:50001/"


@pytest.fixture
def get_coinex_client():
    client = CoinexClientTest(access_id="test", secret="secret")
    yield client


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


class TestFakeExchange:
    def test_fake_exchange(self, fake_exchange):
        for i in range(2):
            response = requests.get(
                f"{CoinexClientTest.BASE_URL}spot/deals", params={"market": "BTC/USDT", "limit": 10}
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("data")[0].get("deal_id") == i + 1

    def test_add_buy_order(self, get_coinex_client, fake_exchange):
        data = {
            "amount": "1",
            "price": "2",
            "side": "buy",
            "market": "BTC/USDT",
            "created": "2024-01-01T00:00:00",
        }
        response = get_coinex_client.order_limit(**data)
        exchange_orders = fake_exchange.get_orders()
        # TODO: continue here
        print(response, exchange_orders)  # to allow pre-commit to pass
