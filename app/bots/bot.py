from app.config.config import Config


class Bot:
    def __init__(self, label: str, exchange: str):
        self.label = label
        self.exchange = exchange
        self.config = Config.load_config_from_db_config(label)

    def run(self):
        print(f"Bot {self.label}/{self.exchange}")
