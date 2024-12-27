import json
import os
from decimal import Decimal
from typing import Any

import yaml
from pydantic import BaseModel, PrivateAttr

from app.common.common import rnd
from app.config.dynamodb import get_dynamodb
from app.config.exchange_decimals import (
    ExchangeDecimals,
    MarketDecimals,
    MarketDecimalsUndefined,
)
from app.models.common import Record
from app.models.price import Price


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
    min_buy_amount_usdt: Decimal

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

    def get_min_buy_amount(self, price: Price):
        return self.rnd_amount(self.min_buy_amount_usdt / price.price)

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


class ConfigValue(BaseModel):
    name: str
    value: Any

    def __init__(self, name: str, value: Any):
        super().__init__(name=name, value=value)
        self.add_private_attribute(name, value)

    def add_private_attribute(self, name: str, value: Any):
        object.__setattr__(self, name, value)


class DbConfig(Record):
    _KEY_FIELD = PrivateAttr(default="key")
    _TABLE_NAME = PrivateAttr(default="config")

    key: str
    values: list[ConfigValue]

    _dvalues: dict[str, Any] = PrivateAttr(default={})

    def add_private_attribute(self, name: str, value: Any):
        object.__setattr__(self, name, value)

    def __init__(self, key: str, values: list[ConfigValue]):
        super().__init__(key=key, values=values)
        for value in self.values:
            self._dvalues[value.name] = value.value
            if value.name in self.__dict__:
                raise RuntimeError(f"Attribute {value.name} already exists in {self.__class__.__name__}")
            self.add_private_attribute(value.name, value.value)

    @classmethod
    def from_db(cls, key: str) -> "DbConfig":
        config = get_dynamodb().Table(cls._TABLE_NAME.get_default()).get_item(Key={"key": key}).get("Item")
        if config:
            values = [ConfigValue(**value) for value in config.get("values", [])]
        else:
            values = []
        return cls(key=key, values=values)

    @classmethod
    def get_full_table_name(cls, bot):
        return cls._TABLE_NAME.get_default()

    @classmethod
    def add_bot(cls, label: str, **kwargs):
        key = f"bot_{label}"
        config = cls.from_db(key)
        for k, v in kwargs.items():
            new_config_value = ConfigValue(name=k, value=v)
            config.values.append(new_config_value)
            config._dvalues[k] = v

        cls.save("N/A", config)

    @classmethod
    def add_decimals_config(cls, exchange: str, pairs: list[dict[str, dict[str, int]]]):
        key = f"decimals_{exchange}"
        config = cls.from_db(key)
        for pair in pairs:
            for k, v in pair.items():
                new_config_value = ConfigValue(name=k, value=v)
                config.values.append(new_config_value)
                config._dvalues[k] = v
        cls.save("N/A", config)

    @classmethod
    def update_config(cls, config: "DbConfig"):
        table = get_dynamodb().Table(cls._TABLE_NAME.get_default())
        item = json.loads(config.model_dump_json())
        try:
            table.put_item(Item=item)
            print(f"{cls.__name__} {config.get_id()} updated successfully in DynamoDB.")
        except Exception as e:
            raise RuntimeError(f"Failed to update {cls.__name__} {config.get_id()} in DynamoDB: {e}")
