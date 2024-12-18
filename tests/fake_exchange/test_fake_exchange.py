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
