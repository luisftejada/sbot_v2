from decimal import Decimal

from pydantic import BaseModel

from app.config.config import Config
from app.models.price import Price


class NotEnoughBalanceException(RuntimeError):
    pass


class NotFoundBalanceException(RuntimeError):
    pass


class Balance(BaseModel):
    currency: str
    available: Decimal = Decimal(0)
    locked_amount: Decimal = Decimal(0)
    rinconcito_usdt: Decimal = Decimal(0)

    @property
    def total(self) -> Decimal:
        return self.available + self.locked_amount

    def inc(self, amount: Decimal):
        self.available += amount

    def lock(self, amount: Decimal):
        self.locked_amount += amount
        self.available -= amount

    def unlock(self, amount: Decimal):
        self.locked_amount -= amount
        self.available += amount

    def dec(self, amount: Decimal):
        self.available -= amount

    def get_coinex_data(self):
        return {"ccy": self.currency, "available": f"{self.available}", "frozen": f"{self.locked_amount}"}

    def rinconcito_amount(self, price: Price) -> Decimal:
        return self.rinconcito_usdt / price.price

    def available_amount(self, price: Price) -> Decimal:
        return self.available - self.rinconcito_amount(price=price)

    @classmethod
    def create_from_coinex(cls, currency: str, data: dict, config: Config) -> "Balance":
        rinconcito_usdt = Decimal(0)
        if currency == config.currency_from:
            rinconcito_usdt = config.min_buy_amount_usdt
        return cls(
            currency=currency,
            available=Decimal(data.get("available", "0")) + Decimal(data.get("frozen", "0")),
            locked_amount=Decimal(
                data.get("frozen", "0"),
            ),
            rinconcito_usdt=rinconcito_usdt,
        )

    @classmethod
    def create_basic_balance(cls, currency: str, config: Config) -> "Balance":
        rinconcito_usdt = Decimal(0)
        if currency == config.currency_from:
            rinconcito_usdt = config.min_buy_amount_usdt
        return cls(currency=currency, available=Decimal(0), locked_amount=Decimal(0), rinconcito_usdt=rinconcito_usdt)
