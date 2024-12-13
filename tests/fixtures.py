import os
from unittest import mock

import pytest
from dotenv import load_dotenv

from app.api.client.coinex import CoinexClient
from app.api.coinex import CoinexApi
from app.config.config import Config

load_dotenv("configurations/test/.env-tests")


class CoinexClientTest(CoinexClient):
    BASE_URL = "http://127.0.0.1:50001/"


def create_config():
    config_file_path = os.environ["CONFIG_FILE"]
    with mock.patch.dict(os.environ, {"P_COINEX_BTC1_V2_ACCESS_KEY": "test", "P_COINEX_BTC1_V2_SECRET_KEY": "secret"}):
        config = Config.read_config_from_yaml(config_file_path)
        return config


@pytest.fixture
def coinex_api(create_config, get_coinex_client) -> CoinexApi:
    config = create_config
    coinex_api = CoinexApi(config)
    coinex_api.client = get_coinex_client
    return coinex_api


@pytest.fixture
def db_session():
    CONNECT_URL = os.environ.get("DATABASE_CONNECT")
    DATABASE_NAME = os.environ.get("DATABASE_NAME")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config.database import Base

    DATABASE_URL = f"{CONNECT_URL}/{DATABASE_NAME}"
    engine = create_engine(DATABASE_URL)
    print(DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    # Teardown
    session.close()
    # Base.metadata.drop_all(bind=engine)


@pytest.fixture
def fake_exchange():
    yield get_fake_exchange()

    reset_exchange()


def get_fake_exchange() -> "CoinexFakeExchange":  # noqa: F821
    from tests.fake_exchange.coinex import CoinexFakeExchange

    exchange = CoinexFakeExchange()
    config = create_config()
    exchange.set_config(config)
    return exchange


_exchange = None


def get_exchange():
    global _exchange
    if _exchange is None:
        _exchange = get_fake_exchange()
    return _exchange


def reset_exchange():
    global _exchange
    _exchange = None
