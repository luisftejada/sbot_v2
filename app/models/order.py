import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, Optional

from pydantic import BaseModel, PrivateAttr
from sqlalchemy import DateTime, Enum, Numeric, String
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.config.config import Config
from app.config.database import Base, get_engine


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
    executed: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    buy_price: Mapped[Numeric] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    sell_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.INITIAL)
    amount: Mapped[Numeric] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    filled: Mapped[Numeric] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    benefit: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    market: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    @classmethod
    def get_by_order_id(cls, order_id: str) -> Optional["DbOrder"]:
        with Session(get_engine()) as session:
            try:
                return session.query(DbOrder).filter_by(order_id=order_id).one()
            except NoResultFound:
                return None


BASIC_CURRENCIES = ["BTC", "USDT", "USDC"]


class Order(BaseModel):
    order_id: str
    created: datetime.datetime
    executed: datetime.datetime | None
    type: OrderType
    buy_price: Decimal | None
    sell_price: Decimal | None
    status: OrderStatus
    amount: Decimal
    filled: Decimal | None
    benefit: Decimal | None
    market: str  # Note market does not include /

    _currency_from: Optional[str] = PrivateAttr(default=None)
    _currency_to: Optional[str] = PrivateAttr(default=None)

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
            market=db_order.market,
        )

    @classmethod
    def create_from_coinex(cls, config: Config, coinex_data: Any, market: str | None = None) -> "Order":
        date = datetime.datetime.fromtimestamp(coinex_data.get("created_at") // 1000)
        order_type = OrderType.from_value(coinex_data.get("side"))
        _market = market if market is not None else config.market
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

        obj = cls(
            order_id=str(coinex_data.get("order_id")),
            created=date,
            executed=None,
            type=order_type.value,
            buy_price=buy_price,
            sell_price=sell_price,
            status=OrderStatus.INITIAL,
            amount=config.rnd_amount(coinex_data.get("amount")),
            filled=None,
            benefit=None,
            market=_market,
        )
        return obj

    def save(self):
        """
        performs an upsert in the database
        """
        data = self.model_dump()
        with Session(get_engine()) as session:
            stmt = insert(DbOrder).values(data)
            upsert_stmt = stmt.on_duplicate_key_update(
                executed=data.get("executed"),
                buy_price=data.get("buy_price"),
                sell_price=data.get("sell_price"),
                status=data.get("status"),
                amount=data.get("amount"),
                filled=data.get("filled"),
                benefit=data.get("benefit"),
                market=data.get("market"),
            )
            session.execute(upsert_stmt)
            session.commit()

    def _update_currencies(self) -> None:
        for currency in BASIC_CURRENCIES:
            if self.market.startswith(currency):
                self._currency_from = currency
                self._currency_to = self.market.replace(currency, "")
                return
        for currency in BASIC_CURRENCIES:
            if self.market.endswith(currency):
                self._currency_to = currency
                self._currency_from = self.market.replace(currency, "")
                return

    def currency_from(self) -> str | None:
        if self._currency_from is None:
            self._update_currencies()
        return self._currency_from

    def currency_to(self) -> str | None:
        if self._currency_to is None:
            self._update_currencies()
        return self._currency_to
