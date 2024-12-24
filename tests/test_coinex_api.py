import datetime
from decimal import Decimal

from dotenv import load_dotenv
from freezegun import freeze_time

from app.models.enums import OrderStatus, OrderType
from app.models.order import Executed, MarketOrderType, Order
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
        fake_exchange = get_exchange(reset=True)
        fake_exchange.add_balance("BTC", Decimal(1))
        balances = coinex_api.get_balances()
        assert len(balances) > 0
        assert balances.get("BTC").available_amount == Decimal(1)

    def test_create_buy_order(self, coinex_api, new_tables):
        fake_exchange = get_exchange(reset=True)
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

    def test_create_sell_order(self, coinex_api, new_tables):
        fake_exchange = get_exchange(reset=True)
        fake_exchange.add_balance("ADA", Decimal(100))
        order = coinex_api.create_sell_order("ADAUSDT", "50", "100")
        db_order = Order.query_first_by_status("ADA1", OrderStatus.INITIAL)
        assert order.order_id == "1"
        assert db_order.order_id == "1"
        assert db_order.amount == Decimal("50")
        assert db_order.buy_price is None
        assert db_order.sell_price == Decimal("100")
        assert db_order.market == "ADAUSDT"
        assert db_order.type == OrderType.SELL
        assert db_order.orderStatus == OrderStatus.INITIAL
        exchange_orders = fake_exchange.get_open_orders()
        assert len(exchange_orders) == 1

    def test_open_orders(self, coinex_api, new_tables):
        fake_exchange = get_exchange(reset=True)
        fake_exchange.add_balance("USDT", Decimal(100000))
        order = coinex_api.create_buy_order("ADAUSDT", "0.5", "100")
        assert order.order_id == "1"
        orders = coinex_api.order_pending("ADAUSDT")
        db_orders = Order.query_by_status("ADA1", OrderStatus.INITIAL)
        assert len(orders) == 1
        assert len(db_orders) == 1
        assert orders[0].order_id == "1"
        assert db_orders[0].order_id == "1"

    def test_cancel_order(self, coinex_api, new_tables):
        fake_exchange = get_exchange(reset=True)
        fake_exchange.add_balance("USDT", Decimal(100000))
        order = coinex_api.create_buy_order("ADAUSDT", "0.5", "100")
        assert order.order_id == "1"
        coinex_api.cancel_order("ADAUSDT", "1")
        exchange_orders = fake_exchange.get_open_orders()
        assert len(exchange_orders) == 0

    def test_get_filled(self, coinex_api, new_tables):
        fake_exchange = get_exchange(reset=True)
        fake_exchange.upload_manual_prices(
            [
                ["2021-01-01T00:00:00", "101"],
                ["2021-01-01T00:00:01", "100"],
                ["2021-01-01T00:01:00", "99"],
                ["2021-01-01T00:02:00", "98"],
            ]
        )
        fake_exchange.add_balance("USDT", Decimal(100000))
        fake_exchange.add_balance("ADA", Decimal(100))
        order = coinex_api.create_buy_order("ADAUSDT", "50", "100")
        assert order.order_id == "1"
        # pass some time to let the exchange execute the buy order
        for _ in range(3):
            fake_exchange.get_current_price()
        last_filled = coinex_api.last_fill
        filled = coinex_api.get_filled(OrderType.BUY, last_filled)
        assert len(filled) > 0

    def test_create_market_order(self, coinex_api, new_tables):
        fake_exchange = get_exchange(reset=True)
        fake_exchange.add_balance("USDT", Decimal(100000))
        fake_exchange.add_balance("ADA", Decimal(100))
        fake_exchange.upload_manual_prices(
            [
                ["2024-01-01T00:00:00", "101"],
                ["2024-01-01T00:00:01", "101"],
            ]
        )
        with freeze_time("2024-01-01"):
            order = coinex_api.create_market_order("ADAUSDT", "0.5", MarketOrderType.BUY)
            all_market_orders = Executed.query_by_day("ADA1", datetime.datetime(2024, 1, 1))
            assert len(all_market_orders) == 1
            assert all_market_orders[0].order_id == order.order_id
