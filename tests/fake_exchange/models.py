from decimal import Decimal

from pydantic import BaseModel


class Balance(BaseModel):
    currency: str
    available_amount: Decimal = Decimal(0)
    locked_amount: Decimal = Decimal(0)

    @property
    def total(self) -> Decimal:
        return self.available_amount + self.locked_amount

    def inc(self, amount: Decimal):
        self.available_amount += amount
        self.locked_amount -= amount

    def dec(self, amount: Decimal):
        self.available_amount -= amount
        self.locked_amount += amount

    def get_coinex_data(self):
        return {"ccy": self.currency, "available": f"{self.available_amount}", "frozen": f"{self.locked_amount}"}
