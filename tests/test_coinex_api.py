import datetime
from decimal import Decimal

from dotenv import load_dotenv

from app.models.order import Order, OrderStatus, OrderType
from tests.conftest import get_exchange

load_dotenv("configurations/test/.env-tests")


class TestCoinexClient:
    def test_coinex_client_market_deals(self, get_coinex_client):
        data = get_coinex_client.market_deals("BTC/USDT")
        assert data[0].get("deal_id") > 0


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

    def test_create_buy_order(self, coinex_api, new_table):
        fake_exchange = get_exchange()
        fake_exchange.add_balance("USDT", Decimal(100000))
        order = coinex_api.create_buy_order("ADAUSDT", "0.5", "99000")
        db_order = Order.query_first_by_status("ADA1", OrderStatus.INITIAL)
        assert order.order_id == "1"
        assert db_order.order_id == "1"
        assert db_order.amount == Decimal("0.5")
        assert db_order.buy_price == Decimal("99000")
        assert db_order.sell_price is None
        assert db_order.market == "ADAUSDT"
        assert db_order.type == OrderType.BUY
        assert db_order.orderStatus == OrderStatus.INITIAL
        exchange_orders = fake_exchange.get_open_orders()
        assert len(exchange_orders) == 1

    def test_open_orders(self, coinex_api):
        fake_exchange = get_exchange()
        fake_exchange.reset()
        fake_exchange.add_balance("USDT", Decimal(100000))
        order = coinex_api.create_buy_order("ADAUSDT", "0.5", "100")
        assert order.order_id == "1"
        orders = coinex_api.order_pending("ADAUSDT")
        db_orders = Order.query_by_status("ADA1", OrderStatus.INITIAL)
        assert len(orders) == 1
        assert len(db_orders) == 1
        assert orders[0].order_id == "1"
        assert db_orders[0].order_id == "1"

    def test_get_filled(self, coinex_api):
        fake_exchange = get_exchange()
        fake_exchange.reset()
        fake_exchange.upload_manual_prices(
            [
                ["2021-01-01T00:00:00", "100001"],
                ["2021-01-01T00:00:01", "100000"],
                ["2021-01-01T00:01:00", "99000"],
                ["2021-01-01T00:02:00", "98000"],
            ]
        )
        fake_exchange.add_balance("USDT", Decimal(100000))
        fake_exchange.add_balance("ADA", Decimal(100))
        order = coinex_api.create_buy_order("ADAUSDT", "50", "100")
        assert order.order_id == "1"
        # pass some time to let the exchange execute the buy order
        for _ in range(3):
            fake_exchange.get_current_price()
