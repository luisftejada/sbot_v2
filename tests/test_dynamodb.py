import datetime
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from app.config import dynamodb
from app.models.common import Record
from app.models.enums import OrderStatus, OrderType
from app.models.order import Order

load_dotenv("configurations/test/.env-tests")


class TestDynamoDb:
    def test_create_table(self, new_tables):
        assert "ADA1_orders" in dynamodb.get_dynamodb().meta.client.list_tables().get("TableNames")
        Order.delete_table("ADA1")
        assert "ADA1_orders" not in dynamodb.get_dynamodb().meta.client.list_tables().get("TableNames")

    def test_add_order(self, new_tables):
        order = Order(
            order_id="1",
            created=datetime.datetime.now(),
            type=OrderType.BUY,
            orderStatus=OrderStatus.INITIAL,
            amount=Decimal("0.1"),
            buy_price=Decimal("1000"),
            executed=None,
            market="BTCUSDT",
        )
        Order.save("ADA1", order)

        assert Order.get("ADA1", "1").order_id == "1"
        Order.delete("ADA1", "1")
        with pytest.raises(Record.NotFoundError):
            Order.get("ADA1", "1")

    def _add_orders(self, itererations, statuses):
        date = datetime.datetime(2024, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
        _id = 0
        for i in range(itererations):
            for status in statuses:
                _id += 1
                order = Order(
                    order_id=str(_id),
                    created=date,
                    type=OrderType.BUY,
                    orderStatus=status,
                    amount=Decimal("0.1"),
                    buy_price=Decimal("1000"),
                    executed=None,
                    market="BTCUSDT",
                )
                Order.save("ADA1", order)
            date += datetime.timedelta(days=1)

    def test_fetch_orders(self, new_tables):
        self._add_orders(10, [OrderStatus.INITIAL, OrderStatus.EXECUTED])
        all_initial_orders = Order.query_by_status("ADA1", OrderStatus.INITIAL)
        assert len(all_initial_orders) == 10
        from_date = datetime.datetime(2024, 1, 5, 0, 0, tzinfo=datetime.timezone.utc)
        to_date = datetime.datetime(2024, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)

        # ascending order
        in_period_initial_orders = Order.query_by_status("ADA1", OrderStatus.INITIAL, from_date, to_date)
        assert len(in_period_initial_orders) == 4
        assert in_period_initial_orders[0].created.day == 5

        # descending order
        in_period_executed_orders = Order.query_by_status(
            "ADA1", OrderStatus.EXECUTED, from_date, to_date, ascending=False
        )
        assert len(in_period_executed_orders) == 4
        assert in_period_executed_orders[0].created.day == 8

        # limit to 1
        first_executed_order = Order.query_by_status(
            "ADA1", OrderStatus.EXECUTED, from_date, to_date, ascending=False, limit=1
        )
        assert len(first_executed_order) == 1

        # empty result
        missing_orders = Order.query_by_status(
            "ADA1",
            OrderStatus.EXECUTED,
            from_date + datetime.timedelta(days=10),
            from_date + datetime.timedelta(days=20),
            limit=1,
        )
        assert len(missing_orders) == 0
