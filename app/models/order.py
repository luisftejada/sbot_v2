from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class OrderType(PyEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(PyEnum):
    INITIAL = "initial"
    CREATED = "created"
    EXECUTED = "executed"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    executed: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    buy_price: Mapped[Numeric] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    sell_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=10, scale=2))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.INITIAL)
    amount: Mapped[Numeric] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    filled: Mapped[Numeric] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    benefit: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=10, scale=2))
