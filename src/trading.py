"""Trading script logic runnable as a module."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

from .portfolio import Portfolio
from .generate_graph import generate_graph
from .cache import get_price_data

# Location of status json relative to project root
STATUS_FILE = Path(__file__).resolve().parents[1] / "bot_status.json"


def _write_status(action: str, file: Path = STATUS_FILE) -> None:
    """Write the last action message to ``file``."""
    data = {"last_action": action, "time": datetime.utcnow().isoformat()}
    with file.open("w") as f:
        json.dump(data, f)


def load_config(path: str) -> dict:
    """Load YAML or JSON configuration file."""
    with open(path, "r") as f:
        if path.endswith(".json"):
            return json.load(f)
        return yaml.safe_load(f)


def daily_results(chatgpt_portfolio: Iterable[dict] | pd.DataFrame,
                  extra_tickers: Iterable[str],
                  today: str) -> None:
    """Print daily price information for tickers."""
    if isinstance(chatgpt_portfolio, pd.DataFrame):
        chatgpt_portfolio = chatgpt_portfolio.to_dict(orient="records")
    print(f"prices and updates for {today}")
    for stock in list(chatgpt_portfolio) + [{"ticker": t} for t in extra_tickers]:
        ticker = stock["ticker"]
        data = get_price_data(ticker, period="2d", date=today)

        # ``get_price_data`` may sometimes return fewer than two rows (for
        # example around holidays or for recently listed tickers). Using
        # ``iloc[-2:]`` followed by ``squeeze`` would return a Series when two
        # rows are present which cannot be directly converted to ``float``.
        close_prices = data["Close"].dropna()
        price = float(close_prices.iloc[-1])
        if len(close_prices) >= 2:
            last_price = float(close_prices.iloc[-2])
        else:
            last_price = price
        percent_change = ((price - last_price) / last_price) * 100
        volume = float(data["Volume"].iloc[-1:].squeeze())
        print(f"{ticker} closing price: {price:.2f}")
        print(f"{ticker} volume for today: ${volume:,}")
        print(f"percent change from the day before: {percent_change:.2f}%")

    chatgpt_df = pd.read_csv("Scripts and CSV Files/chatgpt_portfolio_update.csv")
    chatgpt_totals = chatgpt_df[chatgpt_df["Ticker"] == "TOTAL"].copy()
    chatgpt_totals["Date"] = pd.to_datetime(chatgpt_totals["Date"])
    final_date = chatgpt_totals["Date"].max()
    final_equity = chatgpt_totals.loc[chatgpt_totals["Date"] == final_date, "Total Equity"].iloc[0]
    print(f"Latest ChatGPT Equity: ${final_equity:.2f}")

    russell = get_price_data(
        "^RUT",
        date=today,
        start="2025-06-27",
        end=final_date + pd.Timedelta(days=1),
    ).reset_index()[["Date", "Close"]]

    # ``russell`` is a DataFrame with a single ``Close`` column. To compute the
    # value of $100 invested in the index, grab the first and last closing
    # prices as scalar floats. Using ``iloc[0]`` and ``iloc[-1]`` avoids
    # returning a single-element Series, which previously caused a
    # ``TypeError`` when formatting the value.
    initial_price = float(russell["Close"].iloc[0])
    price_now = float(russell["Close"].iloc[-1])
    scaling_factor = 100 / initial_price
    russell_value = price_now * scaling_factor
    print(f"$100 Invested in the Russell 2000 Index: ${russell_value:.2f}")
    print(f"today's portfolio: {chatgpt_portfolio}")


def run(portfolio_path: str, cash: float | None, config_path: str, *, today: str | None = None) -> None:
    """Execute the trading logic."""
    today = today or datetime.today().strftime("%Y-%m-%d")

    config = load_config(config_path)
    cash = cash if cash is not None else config.get("default_cash", 0.0)
    extra_tickers = config.get("extra_tickers", ["^RUT", "IWO", "XBI"])
    default_stop = config.get("default_stop_loss")

    portfolio_df = pd.read_csv(portfolio_path)
    # Normalize common column names to match the expected lowercase format
    rename_map = {
        "Ticker": "ticker",
        "Shares": "shares",
        "Stop Loss": "stop_loss",
        "Buy Price": "buy_price",
        "Cost Basis": "cost_basis",
    }
    for old, new in rename_map.items():
        if old in portfolio_df.columns and new not in portfolio_df.columns:
            portfolio_df = portfolio_df.rename(columns={old: new})

    # Remove summary rows like "TOTAL" and any rows missing share counts
    if "ticker" in portfolio_df.columns:
        portfolio_df = portfolio_df[~portfolio_df["ticker"].str.upper().eq("TOTAL")]
    if "shares" in portfolio_df.columns:
        portfolio_df = portfolio_df[portfolio_df["shares"].notna()]

    # Derive missing buy price from cost basis and shares
    if "buy_price" not in portfolio_df.columns and {
        "cost_basis",
        "shares",
    }.issubset(portfolio_df.columns):
        with pd.option_context("mode.chained_assignment", None):
            portfolio_df["buy_price"] = portfolio_df["cost_basis"] / portfolio_df[
                "shares"
            ]
    if default_stop is not None:
        if "stop_loss" not in portfolio_df.columns:
            portfolio_df["stop_loss"] = default_stop
        else:
            portfolio_df["stop_loss"] = portfolio_df["stop_loss"].fillna(default_stop)

    portfolio = Portfolio(today=today)
    portfolio.process(portfolio_df, cash)
    daily_results(portfolio_df, extra_tickers, today)

    graphs_dir = Path("graphs")
    graphs_dir.mkdir(exist_ok=True)
    graph_file = graphs_dir / f"performance_{today}.png"
    generate_graph(graph_file.as_posix(), show=False)
    _write_status("trading script executed")


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Process portfolio updates")
    parser.add_argument("--portfolio", required=True,
                        help="CSV with columns ticker, shares, stop_loss, buy_price")
    parser.add_argument("--cash", type=float, help="Starting cash value")
    parser.add_argument("--config", default="config.yaml",
                        help="Path to YAML/JSON configuration file")
    args = parser.parse_args(list(argv) if argv is not None else None)

    run(args.portfolio, args.cash, args.config)


if __name__ == "__main__":
    main()
