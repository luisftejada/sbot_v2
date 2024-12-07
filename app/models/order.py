import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy import DateTime, Enum, Numeric, String
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.config.config import Config
from app.config.database import Base, engine


class OrderTypeError(RuntimeError):
    pass


class OrderType(PyEnum):
    BUY = "buy"
    SELL = "sell"

    @classmethod
    def from_value(cls, value):
        match value:
            case cls.BUY.value:
                return cls.BUY
            case cls.SELL.value:
                return cls.SELL
            case _:
                raise OrderTypeError(f"Wrong OrderType {value}")


class OrderStatusError(RuntimeError):
    pass


class OrderStatus(PyEnum):
    INITIAL = "initial"
    CREATED = "created"
    EXECUTED = "executed"

    @classmethod
    def from_value(cls, value):
        match value:
            case cls.INITIAL.value:
                return cls.INITIAL
            case cls.CREATED.value:
                return cls.CREATED
            case cls.EXECUTED.value:
                return cls.EXECUTED
            case _:
                raise OrderStatusError(f"wrong OrderStatus {value}")


class DbOrder(Base):
    __tablename__ = "orders"
    __primary_key__ = ["order_id"]

    order_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, primary_key=True)
    created: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    executed: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    buy_price: Mapped[Numeric] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    sell_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=10, scale=2))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.INITIAL)
    amount: Mapped[Numeric] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    filled: Mapped[Numeric] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    benefit: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=10, scale=2))

    @classmethod
    def get_by_order_id(cls, order_id: str) -> "DbOrder" | None:
        with Session(engine) as session:
            try:
                return session.query(DbOrder).filter_by(order_id=order_id).one()
            except NoResultFound:
                return None


class Order(BaseModel):
    order_id: str
    created: datetime.datetime
    executed: datetime.datetime | None
    type: OrderStatus
    buy_price: Decimal | None
    sell_price: Decimal | None
    status: OrderStatus
    amount: Decimal
    filled: Decimal | None
    benefit: Decimal | None

    @classmethod
    def create_from_db(cls, db_order: DbOrder) -> "Order":
        return cls(
            order_id=db_order.order_id,
            created=db_order.created,
            executed=db_order.executed,
            type=db_order.type,
            buy_price=db_order.buy_price,
            sell_price=db_order.sell_price,
            status=db_order.status,
            amount=db_order.amount,
            filled=db_order.filled,
            benefit=db_order.benefit,
        )

    @classmethod
    def create_from_coinex(cls, config: Config, coinex_data: Any) -> "Order":
        date = datetime.datetime.fromtimestamp(coinex_data.get("create_time"))
        order_type = OrderType.from_value(coinex_data.get("type"))
        buy_price: Decimal | None = None
        sell_price: Decimal | None = None
        match order_type:
            case OrderType.BUY:
                buy_price = config.rnd_price(coinex_data.get("price"))
                sell_price = None
            case OrderType.SELL:
                sell_price = config.rnd_price(coinex_data.get("price"))
                buy_price = None
            case _:
                raise OrderTypeError(f"worng order type: {order_type}")

        return cls(
            order_id=coinex_data.get("id"),
            created=date,
            executed=None,
            type=order_type,
            buy_price=buy_price,
            sell_price=sell_price,
            status=OrderStatus.INITIAL,
            amount=config.rnd_amount(coinex_data.get("amount")),
            filled=None,
            benefit=None,
        )

    def save(self):
        """
        performs an upsert in the database
        """
        data = self.model_dump()
        with Session(engine) as session:
            stmt = insert(DbOrder).values(data)
            upsert_stmt = stmt.on_duplicate_key_update(
                executed=stmt.executed,
                buy_price=stmt.buy_price,
                sell_price=stmt.sell_price,
                status=stmt.status,
                amount=stmt.amount,
                filled=stmt.filled,
                benefit=stmt.benefit,
            )
            session.execute(upsert_stmt)
            session.commit()
