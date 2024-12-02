from sqlalchemy import Column, String, DateTime, Numeric, Enum
from app.config.database import Base
from enum import Enum as PyEnum


class OrderType(PyEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(PyEnum):
    INITIAL = "initial"
    CREATED = "created"
    EXECUTED = "executed"


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(255), primary_key=True, nullable=False)
    order_id = Column(String(255), unique=True, nullable=False)
    created = Column(DateTime, nullable=False)
    executed = Column(DateTime)
    type = Column(Enum(OrderType), nullable=False)
    buy_price = Column(Numeric(precision=10, scale=2), nullable=False)
    sell_price = Column(Numeric(precision=10, scale=2))
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.INITIAL)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    filled = Column(Numeric(precision=10, scale=2), nullable=False)
    benefit = Column(Numeric(precision=10, scale=2))
