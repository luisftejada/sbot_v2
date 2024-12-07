from app.config.config import Config


def getApi(config: Config):
    match config.exchange:
        case "coinex":
            from app.api.coinex import CoinexApi

            return CoinexApi(config)
        case "binance":
            from app.api.binance import BinanceApi

            return BinanceApi(config)
        case _:
            raise ValueError("Invalid exchange")
