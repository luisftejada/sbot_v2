import os
from typing import List

import yaml
from pydantic import BaseModel

from app.config.exchange_decimals import ExchangeDecimals, MarketDecimals, MarketDecimalsUndefined


# Definimos la clase de modelo Pydantic para validar los datos del YAML
class Config(BaseModel):
    label: str
    exchange: str
    pair: str
    api_version: str
    decimals: ExchangeDecimals


def read_decimals_from_yaml(file_path: str) -> MarketDecimals:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
        return MarketDecimals(**data)


def get_decimals_file() -> str:
    return os.environ.get("DECIMALS_FILE", "")


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

        return Config(**data)
