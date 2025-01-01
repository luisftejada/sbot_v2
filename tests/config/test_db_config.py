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


def test_db_secrets_config(create_table):
    secrets = [{"key1": "value1"}, {"key2": "value2"}]
    DbConfig.add_secrets(secrets=secrets)
    config = DbConfig.from_db("secrets")
    assert config.values[0].name == "key1"
    assert config.values[0].value == "value1"
    assert config.values[1].name == "key2"
    assert config.values[1].value == "value2"


def test_get_all_bots(create_table):
    bots = DbConfig.get_all_bots()
    assert len(bots) == 0
    for ccy in ["ADA", "ETH", "BTC"]:
        DbConfig.add_bot(f"{ccy}1", pair=f"{ccy}/USDT", exchange="coinex", min_buy_amount_usdt=200)
    # add a secret
    DbConfig.add_secrets([{"key1": "value1"}])
    # add some decimals
    DbConfig.add_decimals_config(
        "coinex",
        pairs=[
            {"ADAUSDT": {"amount": 6, "price": 4}},
            {"BTCUSDT": {"amount": 8, "price": 8}},
            {"USDTUSDC": {"amount": 2, "price": 4}},
        ],
    )
    bots = DbConfig.get_all_bots()
    assert len(bots) == 3
