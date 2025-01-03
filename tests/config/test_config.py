import tempfile
from unittest import mock

import pytest
import yaml

from app.config.config import Config
from app.config.exchange_decimals import ExchangeDecimals


# Fixture para crear un archivo YAML temporal con datos proporcionados
@pytest.fixture
def create_temp_yaml():
    def _create_temp_yaml(data):
        with tempfile.NamedTemporaryFile("w", delete=False) as temp_file:
            yaml.dump(data, temp_file)
            return temp_file.name

    return _create_temp_yaml


@pytest.fixture
def create_decimals_file():
    data = {
        "binance": {"pairs": {"BTCUSDT": {"amount": 6, "price": 2}}},
        "coinex": {"pairs": {"BTCUSDT": {"amount": 6, "price": 2}}},
    }
    with tempfile.NamedTemporaryFile("w", delete=False) as temp_file:
        yaml.dump(data, temp_file)
        return temp_file.name


# Fixture para crear un archivo YAML con datos válidos
@pytest.fixture
def create_valid_data_yaml(create_temp_yaml):
    valid_data = {
        "label": "ADA1",
        "exchange": "coinex",
        "market": "BTCUSDT",
        "min_buy_amount_usdt": "200",
        "pair": "ADA1/USDT",
    }
    return create_temp_yaml(valid_data)


# Fixture para crear un archivo YAML con datos inválidos
@pytest.fixture
def create_invalid_data_yaml(create_temp_yaml):
    invalid_data = {
        "label": "ADA1",
        "exchange": "coinex",
        "min_buy_amount_usdt": "200",
        # pair is missing
    }
    return create_temp_yaml(invalid_data)


# Test con datos válidos
def test_read_config_from_yaml_valid(create_valid_data_yaml, create_decimals_file):
    with mock.patch("app.config.config.get_decimals_file", return_value=create_decimals_file):
        temp_file_path = create_valid_data_yaml

        # Leer la configuración del archivo temporal
        result = Config.read_config_from_yaml(temp_file_path)

        assert isinstance(result, Config)
        assert result.label == "ADA1"
        assert result.exchange == "coinex"
        assert result.market == "ADA1USDT"
        assert isinstance(result.decimals, ExchangeDecimals)


# Test con datos inválidos
def test_read_config_from_yaml_invalid(create_invalid_data_yaml, create_decimals_file):
    with mock.patch("app.config.config.get_decimals_file", return_value=create_decimals_file):
        temp_file_path = create_invalid_data_yaml

        # Validar que lanza una excepción
        with pytest.raises(Exception):
            Config.read_config_from_yaml(temp_file_path)
