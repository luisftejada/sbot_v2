import datetime
from decimal import Decimal

from dotenv import load_dotenv

from app.models.enums import MarketOrderType, OrderStatus, OrderType
from app.models.order import Executed, Order

load_dotenv("configurations/test/.env-tests")


class TestExecutedOrders:
    def _create_order(self, order_id):
        return Order(
            order_id=f"{order_id:03}",
            created=datetime.datetime(2024, 1, 1),
            amount=Decimal("0.5"),
            buy_price=Decimal("99000"),
            market="ADAUSDT",
            type=OrderType.BUY,
            orderStatus=OrderStatus.INITIAL,
        )

    def test_add_executing_orders(self, new_tables):
        ex = Executed(bot="ADA1", date=datetime.datetime(2024, 1, 1), pages=[], _page_size=10)
        for i in range(12):
            ex.add_executed_order(self._create_order(i + 1), MarketOrderType.BUY)
        assert len(ex.pages[0].orders) == 10
        assert len(ex.pages[1].orders) == 2
        ex.save()
        all_orders = Executed.query_by_day("ADA1", datetime.datetime(2024, 1, 1))
        assert len(all_orders) == 12

    def test_add_a_lot_of_executed_orders(self, new_tables):
        ex = Executed(bot="ADA1", date=datetime.datetime(2024, 1, 1), pages=[], _page_size=10)

        start = datetime.datetime.now()
        for i in range(1000):
            ex.add_executed_order(self._create_order(i), MarketOrderType.BUY)
        print(f"saving all orders. elapsed={datetime.datetime.now() - start}")
        ex.save()
        print(f"saved ! elapsed={datetime.datetime.now() - start}")
        all_orders = Executed.query_by_day("ADA1", datetime.datetime(2024, 1, 1))
        assert len(all_orders) == 1000
