from decimal import Decimal

from pydantic import BaseModel


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
