from enum import Enum as PyEnum
from typing import Type


class OrderTypeError(RuntimeError):
    pass


class MarketOrderTypeError(RuntimeError):
    pass


class BaseEnumMixin:
    @classmethod
    def get_error_class(cls) -> Type[RuntimeError]:
        return RuntimeError

    @classmethod
    def from_value(cls, value):
        try:
            return next(order for order in cls if order.value == value)
        except StopIteration:
            raise cls.get_error_class(f"Wrong {cls.__name__}: value={value}")


class OrderType(BaseEnumMixin, PyEnum):
    BUY = "buy"
    SELL = "sell"

    @classmethod
    def get_error_class(cls) -> Type[RuntimeError]:
        return OrderTypeError


class MarketOrderType(BaseEnumMixin, PyEnum):
    BUY = "buy"
    SELL = "sell"
    SELL_INCREMENT = "si"
    SELL_BENEFIT = "sb"
    SELL_LIQUIDITY = "sl"

    @classmethod
    def get_error_class(cls):
        return MarketOrderTypeError

    @property
    def side(self):
        return OrderType.BUY if self.value == "buy" else OrderType.SELL


class OrderStatusError(RuntimeError):
    pass


class OrderStatus(BaseEnumMixin, PyEnum):
    INITIAL = "initial"
    EXECUTED = "executed"

    @classmethod
    def get_error_class(cls):
        return OrderStatusError


BASIC_CURRENCIES = ["BTC", "USDT", "USDC"]
