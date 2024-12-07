import datetime
from decimal import Decimal

from app.api.base import BaseApi
from app.api.client.coinex import CoinexClient
from app.config.config import Config
from app.models.balance import Balance
from app.models.price import Price


class FetchBalanceException(RuntimeError):
    def __init__(self):
        self.error = "error fetching balance"
        self.payload = {}


class CoinexApi(BaseApi):
    def __init__(self, config: Config):
        super().__init__(config)
        self.client = CoinexClient(config)
        self.previous_price: Decimal | None = None
        self.config = config

    def get_client(self):
        return CoinexClient(self.config.client.key, self.config.client.secret)

    def fetch_price(self) -> Price:
        price = self.previous_price
        while price == self.previous_price:
            deals = self._execute(self.client.market_deals, self.config.symbol, limit=1, rate=Decimal(1))
            if deals:
                price = self.config.rnd_price(Decimal(deals[0].get("price")))
        self.previous_price = price
        new_price = Price(date=datetime.datetime.now(datetime.timezone.utc), price=price)
        return new_price

    def fetch_currency_price(self, currency) -> Decimal:
        deals = self._execute(self.client.market_deals, f"{currency}USDT", limit=1, rate=Decimal(1))
        if deals:
            return self.config.rnd_price(Decimal(deals[0].get("price")))
        else:
            return Decimal("0")

    def get_balances(self) -> dict[str, Balance]:
        return_balances = {}
        balances = self._execute(self.client.balance_info)
        if balances is None:
            raise FetchBalanceException()

        for currency in self.config.currencies:
            if currency not in balances:
                return_balances[currency] = Balance(currency=currency, total=Decimal(0), locked=Decimal(0))
            else:
                bal = balances.get(currency)
                return_balances[currency] = Balance(
                    currency=currency,
                    total=Decimal(bal.get("available")) + Decimal(bal.get("frozen")),
                    locked=Decimal(bal.get("frozen")),
                )
        return return_balances

    def order_pending(self, market: str, page: int = 1, limit: int = 100, **params):
        pass

    def create_buy_order(self, symbol, amount, price):
        pass
