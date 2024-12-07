import os
from decimal import Decimal
from typing import List

import yaml
from pydantic import BaseModel

from app.common.common import rnd
from app.config.exchange_decimals import (
    ExchangeDecimals,
    MarketDecimals,
    MarketDecimalsUndefined,
)


class ClientCredentials(BaseModel):
    key: str
    secret: str


# Definimos la clase de modelo Pydantic para validar los datos del YAML
class Config(BaseModel):
    label: str
    exchange: str
    pair: str
    decimals: ExchangeDecimals
    client: ClientCredentials

    def rnd_price(self, price: Decimal) -> Decimal:
        price_decimals = self.decimals.pairs[self.symbol].price
        return rnd(price, price_decimals)

    def rnd_amount(self, amount: Decimal) -> Decimal:
        amount_decimals = self.decimals.pairs[self.symbol].amount
        return rnd(amount, amount_decimals)

    @property
    def symbol(self) -> str:
        return self.pair.replace("/", "").upper()


def read_decimals_from_yaml(file_path: str) -> MarketDecimals:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
        return MarketDecimals(**data)


def get_decimals_file() -> str:
    return os.environ.get("DECIMALS_FILE", "")


def get_client_credentials(exchange: str, label: str) -> ClientCredentials:
    access_key_str = f"P_{exchange.upper()}_{label.upper()}_V2_ACCESS_KEY"
    try:
        key = os.environ[access_key_str]
    except KeyError:
        raise ValueError(f"Environment access_key variable for {exchange} and {label} not found")

    secret_key_str = f"P_{exchange.upper()}_{label.upper()}_V2_SECRET_KEY"
    try:
        secret = os.environ[secret_key_str]
    except KeyError:
        raise ValueError(f"Environment secret_key variable for {exchange} and {label} not found")

    return ClientCredentials(key=key, secret=secret)


# Función para leer el archivo YAML y parsearlo a la clase Pydantic
def read_config_from_yaml(file_path: str) -> List[Config]:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
        decimals = read_decimals_from_yaml(get_decimals_file())
        match data.get("exchange", ""):
            case "binance":
                data["decimals"] = decimals.binance
            case "coinex":
                data["decimals"] = decimals.coinex
            case _:
                raise MarketDecimalsUndefined(f"Exchange {data.get('exchange')} not in decimals file")  # noqa E713

        return Config(**data, client=get_client_credentials(data["exchange"], data["label"]))
