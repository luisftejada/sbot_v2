from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    OPEN = "open"
    COMPLETED = "completed"
    CANCELED = "canceled"


class Order(BaseModel):
    pair: str  # e.g., "BTC/USD"
    type: OrderType  # Enum for type
    amount: float
    status: OrderStatus  # Enum for status
    date: datetime = datetime.now()


class Balance(BaseModel):
    currency: str
    available_amount: Decimal = Decimal(0)
    locked_amount: Decimal = Decimal(0)

    def inc(self, amount: Decimal):
        self.available_amount += amount
        self.locked_amount -= amount

    def dec(self, amount: Decimal):
        self.available_amount -= amount
        self.locked_amount += amount
