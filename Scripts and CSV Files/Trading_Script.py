import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import argparse
from pathlib import Path
import sys
import json
import yaml

STATUS_FILE = Path("bot_status.json")

def _write_status(action: str) -> None:
    """Write the last action message to ``bot_status.json``."""
    data = {"last_action": action, "time": datetime.utcnow().isoformat()}
    with STATUS_FILE.open("w") as f:
        json.dump(data, f)

from src.portfolio import Portfolio

sys.path.append("Scripts and CSV Files")

from Generate_Graph import generate_graph
from cache import get_price_data


def load_config(path: str) -> dict:
    """Load YAML or JSON configuration file."""
    with open(path, "r") as f:
        if path.endswith(".json"):
            return json.load(f)
        return yaml.safe_load(f)



# This is where chatGPT gets daily updates from
# I give it data on its portfolio and also other tickers if requested
# Right now it additionally wants "^RUT", "IWO", and "XBI"

def daily_results(chatgpt_portfolio, extra_tickers):
    if isinstance(chatgpt_portfolio, pd.DataFrame):
            chatgpt_portfolio = chatgpt_portfolio.to_dict(orient="records")
    print(f"prices and updates for {today}")
    for stock in chatgpt_portfolio + [{"ticker": t} for t in extra_tickers]:
        ticker = stock['ticker']
        try:
            data = get_price_data(ticker, period="2d", date=today)
            price = float(data['Close'].iloc[-1].item())
            last_price = float(data['Close'].iloc[-2].item())
            percent_change = ((price - last_price) / last_price) * 100
            volume = float(data['Volume'].iloc[-1].item())
        except Exception as e:
            raise KeyError(f"Download for {ticker} failed. Try checking internet connection.")
        print(f"{ticker} closing price: {price:.2f}")
        print(f"{ticker} volume for today: ${volume:,}")
        print(f"percent change from the day before: {percent_change:.2f}%")
    chatgpt_df = pd.read_csv("Scripts and CSV Files/chatgpt_portfolio_update.csv")

    # Filter TOTAL rows and get latest equity
    chatgpt_totals = chatgpt_df[chatgpt_df['Ticker'] == 'TOTAL'].copy() 
    chatgpt_totals['Date'] = pd.to_datetime(chatgpt_totals['Date'])
    final_date = chatgpt_totals['Date'].max()
    final_value = chatgpt_totals[chatgpt_totals['Date'] == final_date]
    final_equity = final_value['Total Equity'].values[0]
    print(f"Latest ChatGPT Equity: ${final_equity:.2f}")

# Define start and end date for Russell 2000

# Get Russell 2000 data
    russell = get_price_data(
        "^RUT",
        date=today,
        start="2025-06-27",
        end=final_date + pd.Timedelta(days=1),
    )
    russell = russell.reset_index()[["Date", "Close"]]


# Normalize to $100
    initial_price = russell["Close"].iloc[0].item()
    price_now = russell["Close"].iloc[-1].item()
    scaling_factor = 100 / initial_price
    russell_value = price_now * scaling_factor
    print(f"$100 Invested in the Russell 2000 Index: ${russell_value:.2f}")
    print(f"today's portfolio: {chatgpt_portfolio}")

    

def main():
    parser = argparse.ArgumentParser(description="Process portfolio updates")
    parser.add_argument(
        "--portfolio",
        required=True,
        help="Path to CSV with columns ticker, shares, stop_loss, buy_price",
    )
    parser.add_argument(
        "--cash",
        type=float,
        help="Starting cash value (overrides config)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to YAML/JSON configuration file",
    )

    args = parser.parse_args()

    config = load_config(args.config)
    cash = args.cash if args.cash is not None else config.get("default_cash", 0.0)
    extra_tickers = config.get("extra_tickers", ["^RUT", "IWO", "XBI"])
    default_stop = config.get("default_stop_loss")

    portfolio_df = pd.read_csv(args.portfolio)
    if default_stop is not None:
        if "stop_loss" not in portfolio_df.columns:
            portfolio_df["stop_loss"] = default_stop
        else:
            portfolio_df["stop_loss"].fillna(default_stop, inplace=True)

    portfolio = Portfolio(today=today)
    portfolio.process(portfolio_df, cash)
    daily_results(portfolio_df, extra_tickers)

    graphs_dir = Path("graphs")
    graphs_dir.mkdir(exist_ok=True)
    graph_file = graphs_dir / f"performance_{today}.png"
    generate_graph(graph_file.as_posix(), show=False)
    _write_status("trading script executed")


if __name__ == "__main__":
    today = datetime.today().strftime("%Y-%m-%d")
    main()
