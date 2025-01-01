import argparse

from app.config.config import DbConfig

# Create the parser
parser = argparse.ArgumentParser(description="Manage trading bot operations.")

# Define subcommands
subparsers = parser.add_subparsers(dest="command", help="Available commands")

# Subcommand: create_table
create_table_parser = subparsers.add_parser("create-table", help="Create the config table")
# No additional arguments required

# Subcommand: add-bot
add_bot_parser = subparsers.add_parser("add-bot", help="Add a new trading bot")
add_bot_parser.add_argument("--label", required=True, type=str, help="The label for the bot")
add_bot_parser.add_argument("--pair", required=True, type=str, help="The trading pair (e.g., BTC/USDT)")
add_bot_parser.add_argument("--exchange", required=True, type=str, help="The exchange to use")
add_bot_parser.add_argument("--min_buy_amount_usdt", required=True, type=float, help="Minimum buy amount in USDT")

# Subcommand: list-bots
list_bots_parser = subparsers.add_parser("list-bots", help="List all trading bots")

# Subcommand: delete-bot
delete_bot_parser = subparsers.add_parser("delete-bot", help="Delete a trading bot")
delete_bot_parser.add_argument("--label", required=True, type=str, help="The label for the bot")

# subcommand: add-bot-config
update_bot_parser = subparsers.add_parser("add-bot-config", help="add a config to a bot")
update_bot_parser.add_argument("--label", required=True, type=str, help="The label for the bot")
update_bot_parser.add_argument("--key", required=True, type=str, help="The key to add")
update_bot_parser.add_argument("--value", required=True, type=str, help="The value to add")

# subcommand: delete-bot-config
update_bot_parser = subparsers.add_parser("delete-bot-config", help="Delete a config from a bot")
update_bot_parser.add_argument("--label", required=True, type=str, help="The label for the bot")
update_bot_parser.add_argument("--key", required=True, type=str, help="The key to delete")

# Subcommand: add-decimals
add_decimals_parser = subparsers.add_parser("add-decimals", help="Add decimals to a market")
add_decimals_parser.add_argument(
    "--exchange", required=True, type=str, help="The exchange", choices=["coinex", "binance"]
)
add_decimals_parser.add_argument("--market", required=True, type=str, help="The market (e.g., BTC/USDT)")
add_decimals_parser.add_argument("--amount", required=True, type=int, help="Number of decimal places for the amount")
add_decimals_parser.add_argument("--price", required=True, type=int, help="Number of decimal places for the price")

# Subcommand: list-decimals
list_decimals_parser = subparsers.add_parser("list-decimals", help="List all decimal configurations")
list_decimals_parser.add_argument("--exchange", required=True, type=str, help="The exchange to use")

# Subcommand: delete-decimals
delete_decimals_parser = subparsers.add_parser("delete-decimals", help="Delete decimal configurations")
delete_decimals_parser.add_argument("--exchange", required=True, type=str, help="The exchange to use")
delete_decimals_parser.add_argument("--market", required=True, type=str, help="The market to use")

# Subcommand: add-secrets
add_secrets_parser = subparsers.add_parser("add-secret", help="Add secrets to the database")
add_secrets_parser.add_argument("--key", required=True, type=str, help="The key to add")
add_secrets_parser.add_argument("--value", required=True, type=str, help="The value to add")

# Subcommand: list-secrets
list_secrets_parser = subparsers.add_parser("list-secrets", help="List all secrets")

# Subcommand: delete-secret
delete_secret_parser = subparsers.add_parser("delete-secret", help="Delete a secret")
delete_secret_parser.add_argument("--key", required=True, type=str, help="The key to delete")

# Parse arguments
args = parser.parse_args()

# Handle subcommands
if args.command == "create-table":
    print("Creating the database table...")
    DbConfig.create_table()

elif args.command == "add-bot":
    print(f"Adding bot with label: {args.label}")
    print(f"Trading pair: {args.pair}")
    print(f"Exchange: {args.exchange}")
    print(f"Minimum buy amount in USDT: {args.min_buy_amount_usdt}")
    DbConfig.add_bot(
        args.label, pair=args.pair, exchange=args.exchange, min_buy_amount_usdt=str(args.min_buy_amount_usdt)
    )
    # Add logic to add the bot here

elif args.command == "list-bots":
    print("Listing all trading bots...")
    bots = DbConfig.get_all_bots()
    for bot in bots:
        print(f"{'- ' * 50}")
        print(f"Bot: {bot.key}")
        for cfg in bot.values:
            print(f"{cfg.name} -> {cfg.value}")

elif args.command == "delete-bot":
    print(f"Deleting bot with label: {args.label}")
    DbConfig.delete_bot(args.label)

elif args.command == "add-bot-config":
    print(f"Adding config to bot with label: {args.label}")
    print(f"Key: {args.key}")
    print(f"Value: {args.value}")
    DbConfig.add_bot_config(args.label, key=args.key, value=args.value)

elif args.command == "delete-bot-config":
    print(f"Deleting config from bot with label: {args.label}")
    print(f"Key: {args.key}")
    DbConfig.delete_bot_config(args.label, args.key)

elif args.command == "add-decimals":
    print(f"Adding decimals for market: {args.market}")
    print(f"Amount decimals: {args.amount}")
    print(f"Price decimals: {args.price}")
    pair = {str(args.market.replace("/", "")): {"amount": str(args.amount), "price": str(args.price)}}
    DbConfig.add_decimals_config(args.exchange, pairs=[pair])  # Add logic to add decimals here

elif args.command == "list-decimals":
    print(f"Listing all decimal configurations for {args.exchange}...")
    decimals = DbConfig.from_db(f"decimals_{args.exchange}")
    for config in decimals.values:
        print(config)

elif args.command == "delete-decimals":
    print(f"Deleting decimals for exchange: {args.exchange} and market: {args.market}")
    pair = args.market.replace("/", "")
    DbConfig.delete_decimals_config(args.exchange, market=args.market)
    # Add logic to delete decimals here

elif args.command == "add-secret":
    print(f"Adding secret: {args.key} -> {args.value}")
    secrets = [{args.key: args.value}]
    DbConfig.add_secrets(secrets=secrets)

elif args.command == "list-secrets":
    print("Listing all secrets...")
    secrets = DbConfig.from_db("secrets")
    for secret in secrets.values:
        print(f"{secret.name} -> {secret.value}")

elif args.command == "delete-secret":
    print(f"Deleting secret with key: {args.key}")
    DbConfig.delete_secret(args.key)

else:
    print("Invalid command. Use --help for usage information.")
