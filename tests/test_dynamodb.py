import datetime
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from app.config import dynamodb
from app.models.common import Record
from app.models.order import Order, OrderStatus, OrderType

load_dotenv("configurations/test/.env-tests")


class TestDynamoDb:
    def test_create_table(self):
        Order.create_table("ADA1")
        assert "ADA1_orders" in dynamodb.get_dynamodb().meta.client.list_tables().get("TableNames")
        Order.delete_table("ADA1")
        assert "ADA1_orders" not in dynamodb.get_dynamodb().meta.client.list_tables().get("TableNames")

    def test_add_order(self):
        Order.create_table("ADA1")
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

    def test_fetch_orders(self):
        Order.delete_table("ADA1")
        Order.create_table("ADA1")
        date = datetime.datetime(2024, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
        _id = 0
        for i in range(10):
            for status in [OrderStatus.INITIAL, OrderStatus.EXECUTED]:
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

        all_created_orders = Order.query_by_status("ADA1", OrderStatus.INITIAL)
        assert len(all_created_orders) == 10

        in_period_executed_orders = Order.query_by_status(
            "ADA1",
            OrderStatus.EXECUTED,
            datetime.datetime(2024, 1, 5, 0, 0, tzinfo=datetime.timezone.utc),
            datetime.datetime(2024, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
        )
        assert len(in_period_executed_orders) == 5  # 5, 6, 7, 8, 9
        assert in_period_executed_orders[0].executed.day == 5
        assert in_period_executed_orders[-1].executed.day == 9
