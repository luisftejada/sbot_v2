import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, PrivateAttr

from app.models.common import Record
from app.models.enums import OrderType


class DbFill(Record):
    _KEY_FIELD: str = PrivateAttr(default="bot")
    _TABLE_NAME: str = PrivateAttr(default="fills")

    bot: str
    buy_fill_id: Optional[str]
    sell_fill_id: Optional[str]
    buy_date: Optional[datetime.datetime] = None
    sell_date: Optional[datetime.datetime] = None

    @classmethod
    def get_full_table_name(cls, bot: str):
        return cls.table_name()

    @classmethod
    def get(cls, bot: str, id: str, raise_not_found: bool = True) -> Optional["Record"]:
        return super().get(bot, id, raise_not_found=False)


class Fill(BaseModel):
    fill_id: str
    amount: Decimal
    price: Decimal
    side: OrderType

    @classmethod
    def from_coinex(cls, record: dict):
        return cls(
            fill_id=str(record.get("deal_id")),
            amount=Decimal(record.get("amount", "0")),
            price=Decimal(record.get("price", "0")),
            side=OrderType(record.get("side", "buy")),
        )


def fill_parser(value) -> list[Fill]:
    return []
