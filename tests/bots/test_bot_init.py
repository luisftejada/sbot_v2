from app.bots.bot import Bot


def test_bot_init(load_db_config):
    bot = Bot("ADA1", "coinex")
    bot.run()
