from enum import Enum as PyEnum


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
    EXECUTED = "executed"

    @classmethod
    def from_value(cls, value):
        match value:
            case cls.INITIAL.value:
                return cls.INITIAL
            case cls.EXECUTED.value:
                return cls.EXECUTED
            case _:
                raise OrderStatusError(f"wrong OrderStatus {value}")


BASIC_CURRENCIES = ["BTC", "USDT", "USDC"]
