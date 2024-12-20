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
            status=OrderStatus.CREATED,
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
