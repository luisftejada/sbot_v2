import datetime
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, field_validator

from app.models.enums import OrderType
from app.models.order import Order


class Balance(BaseModel):
    currency: str
    available_amount: Decimal = Decimal(0)
    locked_amount: Decimal = Decimal(0)

    @property
    def total(self) -> Decimal:
        return self.available_amount + self.locked_amount

    def inc(self, amount: Decimal):
        self.available_amount += amount

    def lock(self, amount: Decimal):
        self.locked_amount += amount
        self.available_amount -= amount

    def unlock(self, amount: Decimal):
        self.locked_amount -= amount
        self.available_amount += amount

    def dec(self, amount: Decimal):
        self.available_amount -= amount

    def get_coinex_data(self):
        return {"ccy": self.currency, "available": f"{self.available_amount}", "frozen": f"{self.locked_amount}"}


class BuyOrderData(BaseModel):
    order_id: str
    market: str
    market_type: str
    side: str
    type: str
    ccy: str
    amount: Decimal
    price: Decimal
    created_at: int

    @property
    def updated_at(self) -> int:
        return self.created_at

    @field_validator("created_at", mode="before")
    def parse_created_at(cls, value: Union[int, str, datetime.datetime]) -> int:
        # Convert input into datetime object
        if isinstance(value, (int, float)):  # Assume timestamp
            return int(value)
        if isinstance(value, str):  # Assume ISO 8601 format or similar
            return int(datetime.datetime.fromisoformat(value).timestamp() * 1000)
        return int(value.timestamp() * 1000)  # Assume it's already a datetime object

    def dict(self, **kwargs):
        # Customize serialization
        result = super().dict(**kwargs)
        result["created_at"] = int(self.date.timestamp() * 1000)
        return result

    class Config:
        json_encoders = {datetime: lambda v: int(v.timestamp() * 1000)}


class OrderResponse(BaseModel):
    code: int = 0
    data: BuyOrderData

    @classmethod
    def get_side(cls) -> str:
        return OrderType.BUY.value

    @classmethod
    def get_price(cls, order: Order) -> Decimal:
        return order.buy_price

    @classmethod
    def from_order(cls, order: Order):
        data = {
            "order_id": str(order.order_id),
            "market": order.market,
            "market_type": "spot",
            "side": cls.get_side(),
            "type": "limit",
            "ccy": order.currency_from(),
            "amount": order.amount,
            "price": cls.get_price(order),
            "created_at": order.created.timestamp() * 1000,
            "updated_at": order.created.timestamp() * 1000,
        }
        return cls(code=0, data=data)


class BuyOrderResponse(OrderResponse):
    @classmethod
    def get_side(cls) -> str:
        return OrderType.BUY.value

    @classmethod
    def get_price(cls, order: Order) -> Decimal:
        return order.buy_price


class SellOrderResponse(OrderResponse):
    @classmethod
    def get_side(cls) -> str:
        return OrderType.SELL.value

    @classmethod
    def get_price(cls, order: Order) -> Decimal:
        return order.sell_price


class OrderPendingResponse(BaseModel):
    code: int = 0
    data: list[BuyOrderData]
    pagination: dict[str, Union[int, bool]]
    message: str = "OK"

    @classmethod
    def from_orders(cls, orders: list[Order]):
        data = [BuyOrderData.from_order(order) for order in orders]
        return cls(code=0, data=data, pagination={"total": len(data), "has_next": False}, message="OK")
