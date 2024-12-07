import datetime
from decimal import Decimal

import pydantic


class Price(pydantic.BaseModel):
    price: Decimal
    date: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
