import os
import time
from datetime import datetime, timedelta

import requests


def _d(int_date: int) -> str:
    d = datetime.utcfromtimestamp(int_date / 1000)
    return f"{d.year}-{d.month:02d}-{d.day:02d} {d.hour:02d}:{d.minute:02d}:{d.second:02d}"


def fetch_agg_trades(symbol, start_time, end_time):
    """
    Fetch aggregated trade data from Binance API within a given time range.
    """
    url = "https://api.binance.com/api/v3/aggTrades"
    all_data = []

    i = 0
    while start_time < end_time:
        time.sleep(0.2)
        if i % 10 == 0:
            print(f"      loading from {_d(start_time)} to {_d(end_time)}...")
        i += 1
        params = {"symbol": symbol, "startTime": start_time, "endTime": end_time, "limit": 100000}  # Max per request
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for HTTP issues
        data = response.json()

        if not data:
            break

        all_data.extend(data)
        start_time = data[-1]["T"] + 1  # Update to fetch the next batch

    return all_data


def save_agg_trades_incrementally(data, pair, year, month):
    """
    Save aggregated trade data incrementally to the corresponding file.
    """
    folder_name = f"{year}_{pair}"
    os.makedirs(folder_name, exist_ok=True)

    file_name = f"{year}_{month:02d}_{pair}.txt"  # noqa: E231
    file_path = os.path.join(folder_name, file_name)

    with open(file_path, "a") as file:  # Append mode
        for entry in data:
            timestamp = datetime.utcfromtimestamp(entry["T"] / 1000).isoformat()  # Trade time
            price = entry["p"]  # Price
            file.write(f"{timestamp},{price}\n")  # noqa: E231


def process_date_range(pair, start_date, end_date):
    """
    Process data day by day and save incrementally.
    """
    current_date = start_date

    while current_date < end_date:
        next_date = current_date + timedelta(days=1)

        # Convert to timestamps in milliseconds
        start_time = int(current_date.timestamp() * 1000)
        end_time = int(next_date.timestamp() * 1000)

        print(f"Fetching aggregated trades for {current_date.strftime('%Y-%m-%d')}...")

        # Fetch aggregated trades for the current day
        daily_data = fetch_agg_trades(pair, start_time, end_time)

        # Save incrementally
        year, month = current_date.year, current_date.month
        save_agg_trades_incrementally(daily_data, pair, year, month)

        current_date = next_date  # Move to the next day


def main(pair, from_date, to_date):
    """
    Main script logic.
    """
    # Convert input dates to datetime objects
    start_date = datetime.strptime(from_date, "%Y-%m-%d")
    end_date = datetime.strptime(to_date, "%Y-%m-%d")

    print(f"Fetching aggregated trades for {pair} from {from_date} to {to_date}...")

    # Process the date range
    process_date_range(pair, start_date, end_date)

    print("Download complete!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download aggregated trade data from Binance.")
    parser.add_argument("pair", type=str, help="Trading pair, e.g., ADAUSDT")
    parser.add_argument("from_date", type=str, help="Start date in YYYY-MM-DD format")
    parser.add_argument("to_date", type=str, help="End date in YYYY-MM-DD format")

    args = parser.parse_args()

    main(args.pair, args.from_date, args.to_date)
