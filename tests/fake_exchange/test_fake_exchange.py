import requests

from tests.conftest import CoinexClientTest


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
