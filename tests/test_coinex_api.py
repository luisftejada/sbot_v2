import datetime
from decimal import Decimal

from dotenv import load_dotenv

from app.models.order import DbOrder
from tests.fake_exchange.coinex import get_exchange

load_dotenv("configurations/test/.env-tests")


class TestCoinexClient:
    def test_coinex_client_market_deals(self, get_coinex_client):
        data = get_coinex_client.market_deals("BTC/USDT")
        assert data[0].get("deal_id") > 0


class TestCoinexApi:
    def _test_fetch_price(self, coinex_api):
        price = coinex_api.fetch_price()
        assert price.price > 0
        assert price.date is not None
        assert price.date.tzinfo is not None
        assert price.date.tzinfo == datetime.timezone.utc

    def _test_fetch_currency_price(self, coinex_api):
        price = coinex_api.fetch_currency_price("BTC")
        assert price > 0

    def _test_get_balance_info(self, coinex_api):
        fake_exchange = get_exchange()
        fake_exchange.add_balance("BTC", Decimal(1))
        balances = coinex_api.get_balances()
        assert len(balances) > 0
        assert balances.get("BTC").available_amount == Decimal(1)

    def _test_open_orders(self, coinex_api, db_session):
        fake_exchange = get_exchange()
        fake_exchange.db.add_buy_order("BTC", "0.5", "99000")
        orders = coinex_api.order_pending("BTCUSDT")
        db_orders = db_session.query(DbOrder).all()
        assert len(orders) == 1
        assert len(db_orders) == 1
        assert orders[0].order_id == "1"
        assert db_orders[0].order_id == "1"
