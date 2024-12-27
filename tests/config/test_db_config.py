import pytest

from app.config.config import DbConfig
from app.config.dynamodb import get_dynamodb


@pytest.fixture
def create_table():
    DbConfig.create_table()
    yield
    DbConfig.delete_table()


def test_create_table(create_table):
    assert DbConfig._TABLE_NAME.get_default() in get_dynamodb().meta.client.list_tables()["TableNames"]


def test_add_bot_config(create_table):
    label = "ADA1"
    pair = "ADA1/USDT"
    exchange = "coinex"
    min_buy_amount_usdt = 200
    DbConfig.add_bot(label, pair=pair, exchange=exchange, min_buy_amount_usdt=min_buy_amount_usdt)
    config2 = DbConfig.from_db(f"bot_{label}")
    assert config2.pair == pair
    assert config2.exchange == exchange
    assert config2.min_buy_amount_usdt == min_buy_amount_usdt


def test_add_decimals_config(create_table):
    exchange = "coinex"
    pairs = [{"BTCUSDT": {"amount": 6, "price": 2}}, {"ETHUSDT": {"amount": 4, "price": 3}}]
    DbConfig.add_decimals_config(exchange, pairs=pairs)
    config2 = DbConfig.from_db(f"decimals_{exchange}")
    assert config2.values[0].BTCUSDT == {"amount": 6, "price": 2}
    assert config2.values[1].ETHUSDT == {"amount": 4, "price": 3}
