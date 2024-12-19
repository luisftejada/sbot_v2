import os
from decimal import Decimal

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._currency_from, self._currency_to = self.pair.split("/")
        self._currencies = set([self._currency_from, self._currency_to, "BTC", "USDT", "USDC"])

    def rnd_price(self, price: Decimal, cls: type = Decimal) -> Decimal:
        price_decimals = self.decimals.pairs[self.market].price
        return rnd(price, price_decimals)

    def rnd_amount(self, amount: Decimal, cls: type = Decimal) -> Decimal:
        amount_decimals = self.decimals.pairs[self.market].amount
        return rnd(amount, amount_decimals, cls=cls)

    def rnd_amount_by_ccy(self, amount: Decimal, currency: str, cls: type = Decimal) -> Decimal:
        match currency:
            case "BTC":
                amount_decimals = 8
            case "USDT":
                amount_decimals = 2
            case "USDC":
                amount_decimals = 2
            case _:
                amount_decimals = 8
        return rnd(amount, amount_decimals, cls=cls)

    @property
    def market(self) -> str:
        return self.pair.replace("/", "").upper()

    @property
    def currencies(self):
        return self._currencies

    @property
    def currency_from(self):
        return self._currency_from

    @property
    def currency_to(self):
        return self._currency_to

    # Función para leer el archivo YAML y parsearlo a la clase Pydantic
    @classmethod
    def read_config_from_yaml(cls, file_path: str) -> "Config":
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
            decimals = read_decimals_from_yaml(get_decimals_file(data))
            match data.get("exchange", ""):
                case "binance":
                    data["decimals"] = decimals.binance
                case "coinex":
                    data["decimals"] = decimals.coinex
                case _:
                    raise MarketDecimalsUndefined(f"Exchange {data.get('exchange')} not in decimals file")  # noqa E713

            return cls(**data, client=get_client_credentials(data["exchange"], data["label"]))


def read_decimals_from_yaml(file_path: str) -> MarketDecimals:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
        return MarketDecimals(**data)


def get_decimals_file(data: dict) -> str:
    if "decimals_file_path" in data:
        return data["decimals_file_path"]
    else:
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
