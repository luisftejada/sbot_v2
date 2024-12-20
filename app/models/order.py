import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, Optional

from pydantic import BaseModel, PrivateAttr

from app.config.config import Config
from app.models.common import Index, IndexField, Record, parse_value


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


BASIC_CURRENCIES = ["BTC", "USDT", "USDC"]


class Order(Record):
    _KEY_FIELD: str = PrivateAttr(default="order_id")
    _TABLE_NAME: str = PrivateAttr(default="orders")
    _indexes: list[Index] = PrivateAttr(
        default=[
            Index(
                partition_key=IndexField(field_name="executed", key_type="HASH"),
                sort_key=IndexField(field_name="order_id", key_type="RANGE"),
            )
        ]
    )

    order_id: str
    created: datetime.datetime
    executed: Optional[datetime.datetime] = None
    type: OrderType
    buy_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    status: OrderStatus
    amount: Decimal
    filled: Optional[Decimal] = None
    benefit: Optional[Decimal] = None
    market: str  # Note market does not include /

    _currency_from: Optional[str] = PrivateAttr(default=None)
    _currency_to: Optional[str] = PrivateAttr(default=None)

    @classmethod
    def create_from_db(cls, db_order: dict) -> "Order":
        try:
            # Return the populated Order instance with direct parsing and conversion
            return cls(
                order_id=parse_value(db_order, "order_id"),
                created=parse_value(db_order, "created", datetime.datetime),
                executed=parse_value(db_order, "executed", datetime.datetime, default=None),
                type=parse_value(db_order, "type", OrderType),
                buy_price=parse_value(db_order, "buy_price", Decimal, default=None),
                sell_price=parse_value(db_order, "sell_price", Decimal, default=None),
                status=parse_value(db_order, "status", OrderStatus),
                amount=parse_value(db_order, "amount", Decimal),
                filled=parse_value(db_order, "filled", Decimal, default=None),
                benefit=parse_value(db_order, "benefit", Decimal, default=None),
                market=parse_value(db_order, "market"),
            )
        except KeyError as e:
            raise cls.ParsingError(f"Missing required field in database record: {e}")
        except Exception as e:
            raise ValueError(f"Error creating Order from database record: {e}")

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


class DbOrder(BaseModel):
    pass
