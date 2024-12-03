from typing import Optional

import yaml
from pydantic import BaseModel


class MarketDecimalsUndefined(Exception):
    pass


# Define a model for each pair with 'amount' and 'price'
class Pair(BaseModel):
    amount: Optional[int]
    price: Optional[int]


# Define a model for each exchange, which contains pairs
class ExchangeDecimals(BaseModel):
    pairs: dict[str, Pair]


# Define the top-level model which contains exchanges
class MarketDecimals(BaseModel):
    binance: ExchangeDecimals
    coinex: ExchangeDecimals


# Function to read the YAML file and parse it into Pydantic models
def read_market_decimals(file_path: str) -> MarketDecimals:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
        return MarketDecimals(**data)
