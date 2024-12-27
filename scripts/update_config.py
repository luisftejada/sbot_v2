import argparse

from app.config.config import DbConfig

# Create the parser
parser = argparse.ArgumentParser(description="Manage trading bot operations.")

# Define subcommands
subparsers = parser.add_subparsers(dest="command", help="Available commands")

# Subcommand: create_table
create_table_parser = subparsers.add_parser("create_table", help="Create the database table")
create_table_parser.add_argument("--version", required=True, type=str, help="The version of the configuration")
# No additional arguments required

# Subcommand: add-bot
add_bot_parser = subparsers.add_parser("add-bot", help="Add a new trading bot")
add_bot_parser.add_argument("--version", required=True, type=str, help="The version of the configuration")
add_bot_parser.add_argument("--label", required=True, type=str, help="The label for the bot")
add_bot_parser.add_argument("--pair", required=True, type=str, help="The trading pair (e.g., BTC/USDT)")
add_bot_parser.add_argument("--exchange", required=True, type=str, help="The exchange to use")
add_bot_parser.add_argument("--min_buy_amount_usdt", required=True, type=float, help="Minimum buy amount in USDT")

# Subcommand: add-decimals
add_decimals_parser = subparsers.add_parser("add-decimals", help="Add decimals to a market")
add_decimals_parser.add_argument("--version", required=True, type=str, help="The version of the configuration")
add_decimals_parser.add_argument("--market", required=True, type=str, help="The market (e.g., BTC/USDT)")
add_decimals_parser.add_argument("--amount", required=True, type=int, help="Number of decimal places for the amount")
add_decimals_parser.add_argument("--price", required=True, type=int, help="Number of decimal places for the price")

# Parse arguments
args = parser.parse_args()

# Handle subcommands
if args.command == "create_table":
    print("Creating the database table...")
    DbConfig.create_table()

elif args.command == "add-bot":
    print(f"Adding bot with label: {args.label}")
    print(f"Trading pair: {args.pair}")
    print(f"Exchange: {args.exchange}")
    print(f"Minimum buy amount in USDT: {args.min_buy_amount_usdt}")
    # Add logic to add the bot here
elif args.command == "add-decimals":
    print(f"Adding decimals for market: {args.market}")
    print(f"Amount decimals: {args.amount}")
    print(f"Price decimals: {args.price}")
    # Add logic to add decimals here
else:
    print("Invalid command. Use --help for usage information.")
