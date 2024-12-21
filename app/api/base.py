import time
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

import requests

from app.config.config import Config
from app.models.balance import Balance
from app.models.enums import OrderType
from app.models.filled import Fill
from app.models.order import Order
from app.models.price import Price


def retry_request(func, retries=3, backoff_factor=1, *args, **kwargs):
    """
    Función para realizar reintentos de una función dada.

    :param func: Función a ejecutar (como `_v2`).
    :param retries: Número máximo de reintentos.
    :param backoff_factor: Factor de espera exponencial entre reintentos.
    :param args: Argumentos posicionales para la función.
    :param kwargs: Argumentos de palabra clave para la función.
    :return: Resultado de la función si es exitosa.
    :raises: Excepción si los reintentos fallan.
    """
    attempt = 0
    while attempt <= retries:
        try:
            return func(*args, **kwargs)  # Llamada a la función original
        except requests.exceptions.RequestException as e:
            attempt += 1
            if attempt > retries:
                print(f"Error tras {retries} reintentos: {e}")
                raise
            # Log para depuración
            print(
                f"Intento {attempt}/{retries} fallido. Error: {e}. Reintentando en {backoff_factor ** attempt} segundos..."
            )
            time.sleep(backoff_factor**attempt)  # Exponencial


def with_retries(retries=3, backoff_factor=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return retry_request(func, retries, backoff_factor, *args, **kwargs)

        return wrapper

    return decorator


class BaseApi(ABC):
    def __init__(self, config: Config):
        self.config = config
        self.client = self.get_client()

    @with_retries(retries=3, backoff_factor=1)
    def _execute(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    @abstractmethod
    def get_client(self):
        raise NotImplementedError()

    @abstractmethod
    def fetch_price(self) -> Price:
        raise NotImplementedError()

    @abstractmethod
    def fetch_currency_price(self, currency) -> Decimal:
        raise NotImplementedError

    @abstractmethod
    def get_balances(self) -> dict[str, Balance]:
        raise NotImplementedError

    @abstractmethod
    def order_pending(self, market: str, page: int = 1, limit: int = 100, **params):
        raise NotImplementedError

    @abstractmethod
    def create_buy_order(self, market: str, amount: Decimal, price: Decimal) -> Order:
        raise NotImplementedError

    @abstractmethod
    def get_filled(self, side: OrderType, fill: Fill | None, pair: Optional[str] = None) -> list[Fill]:
        raise NotImplementedError
