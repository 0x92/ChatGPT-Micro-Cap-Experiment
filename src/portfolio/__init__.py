"""Portfolio management helpers."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
import yfinance as yf
from ..broker import place_order
from ..notifications import send_notification


class Portfolio:
    """Utility class implementing the previous module functions."""

    def __init__(self, today: str | None = None) -> None:
        self.today = today or datetime.today().strftime("%Y-%m-%d")

    async def _fetch_history(self, ticker: str):
        data = await asyncio.to_thread(yf.Ticker(ticker).history, period="1d")
        return ticker, data

    async def _download_all(self, tickers: List[str]):
        tasks = [self._fetch_history(t) for t in tickers]
        results = await asyncio.gather(*tasks)
        return {t: d for t, d in results}

    def process(self, portfolio: pd.DataFrame | str, starting_cash: float) -> str:
        if isinstance(portfolio, str):
            portfolio = pd.read_csv(portfolio)

        # Normalize column names if they come from a daily update CSV
        rename_map = {
            "Ticker": "ticker",
            "Shares": "shares",
            "Stop Loss": "stop_loss",
            "Buy Price": "buy_price",
            "Cost Basis": "cost_basis",
        }
        for old, new in rename_map.items():
            if old in portfolio.columns and new not in portfolio.columns:
                portfolio = portfolio.rename(columns={old: new})

        tickers = portfolio["ticker"].tolist()
        price_map = asyncio.run(self._download_all(tickers))

        results: List[Dict[str, Any]] = []
        total_value = 0.0
        total_pnl = 0.0
        cash = starting_cash

        for _, stock in portfolio.iterrows():
            ticker = stock["ticker"]
            shares = int(stock["shares"])
            cost = stock["buy_price"]
            stop = stock["stop_loss"]
            data = price_map.get(ticker, pd.DataFrame())

            if data.empty:
                print(f"Warning: no price history for {ticker}, skipping")
                continue

            price = round(data["Close"].iloc[-1], 2)
            value = round(price * shares, 2)
            pnl = round((price - cost) * shares, 2)

            if price <= stop:
                action = "SELL - Stop Loss Triggered"
                cash += value
                self.log_sell(ticker, shares, price, cost, pnl, action)
            else:
                action = "HOLD"
                total_value += value
                total_pnl += pnl

            results.append({
                "Date": self.today,
                "Ticker": ticker,
                "Shares": shares,
                "Cost Basis": cost,
                "Stop Loss": stop,
                "Current Price": price,
                "Total Value": value,
                "PnL": pnl,
                "Action": action,
                "Cash Balance": "",
                "Total Equity": "",
            })

        total_row = {
            "Date": self.today,
            "Ticker": "TOTAL",
            "Shares": "",
            "Cost Basis": "",
            "Stop Loss": "",
            "Current Price": "",
            "Total Value": round(total_value, 2),
            "PnL": round(total_pnl, 2),
            "Action": "",
            "Cash Balance": round(cash, 2),
            "Total Equity": round(total_value + cash, 2),
        }
        results.append(total_row)

        file = "Scripts and CSV Files/chatgpt_portfolio_update.csv"
        df = pd.DataFrame(results)

        if os.path.exists(file):
            existing = pd.read_csv(file)
            existing = existing[existing["Date"] != self.today]
            df = pd.concat([existing, df], ignore_index=True)

        df.to_csv(file, index=False)
        try:
            from dashboard.audit import record_change
            record_change("system", "portfolio_update", {"file": file})
        except Exception:
            pass
        return file

    def log_sell(
        self,
        ticker: str,
        shares: int,
        price: float,
        cost: float,
        pnl: float,
        reason: str = "AUTOMATED SELL - STOPLOSS TRIGGERED",
    ) -> None:
        log = {
            "Date": self.today,
            "Ticker": ticker,
            "Shares Sold": shares,
            "Sell Price": price,
            "Cost Basis": cost,
            "PnL": pnl,
            "Reason": reason,
        }

        file = "Scripts and CSV Files/chatgpt_trade_log.csv"
        if os.path.exists(file):
            df = pd.read_csv(file)
            df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
        else:
            df = pd.DataFrame([log])
        df.to_csv(file, index=False)

        send_notification(
            f"Sold {shares} shares of {ticker} at {price} (PnL: {pnl:.2f}). Reason: {reason}"
        )

    def log_manual_buy(
        self,
        buy_price: float,
        shares: int,
        ticker: str,
        cash: float,
        stoploss: float,
        chatgpt_portfolio: pd.DataFrame | List[Dict[str, Any]],
    ):
        check = input(
            f"You are currently trying to buy {ticker}. If this a mistake enter 1."
        )
        if check == "1":
            raise SystemExit("Please remove this function call.")

        data = yf.download(ticker, period="1d")
        if data.empty:
            raise SystemExit(f"error, could not find ticker {ticker}")
        if buy_price * shares > cash:
            raise SystemExit(
                f"error, you have {cash} but are trying to spend {buy_price * shares}. Are you sure you can do this?"
            )
        pnl = 0.0

        log = {
            "Date": self.today,
            "Ticker": ticker,
            "Shares Bought": shares,
            "Buy Price": buy_price,
            "Cost Basis": buy_price * shares,
            "PnL": pnl,
            "Reason": "MANUAL BUY - New position",
        }

        file = "Scripts and CSV Files/chatgpt_trade_log.csv"
        if os.path.exists(file):
            df = pd.read_csv(file)
            df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
        else:
            df = pd.DataFrame([log])
        df.to_csv(file, index=False)
        try:
            from dashboard.audit import record_change
            record_change("manual", "trade_buy", log)
        except Exception:
            pass

        send_notification(
            f"Bought {shares} shares of {ticker} at {buy_price}."
        )

        new_trade = {
            "ticker": ticker,
            "shares": shares,
            "stop_loss": stoploss,
            "buy_price": buy_price,
            "cost_basis": buy_price * shares,
        }
        new_trade = pd.DataFrame([new_trade])
        if isinstance(chatgpt_portfolio, list):
            chatgpt_portfolio = pd.DataFrame(chatgpt_portfolio)
        chatgpt_portfolio = pd.concat([chatgpt_portfolio, new_trade], ignore_index=True)
        cash = cash - shares * buy_price
        return cash, chatgpt_portfolio

    def log_manual_sell(
        self,
        sell_price: float,
        shares_sold: int,
        ticker: str,
        cash: float,
        chatgpt_portfolio: pd.DataFrame | List[Dict[str, Any]],
    ):
        if isinstance(chatgpt_portfolio, list):
            chatgpt_portfolio = pd.DataFrame(chatgpt_portfolio)
        if ticker not in chatgpt_portfolio["ticker"].values:
            raise KeyError(f"error, could not find {ticker} in portfolio")
        ticker_row = chatgpt_portfolio[chatgpt_portfolio["ticker"] == ticker]

        total_shares = int(ticker_row["shares"].item())
        if shares_sold > total_shares:
            raise ValueError(
                f"You are trying to sell {shares_sold} but only own {total_shares}."
            )

        buy_price = float(ticker_row["buy_price"].item())

        reason = input("Why are you selling?\nIf this is a mistake, enter 1. ")
        if reason == "1":
            raise SystemExit("Delete this function call from the program.")

        cost_basis = buy_price * shares_sold
        pnl = sell_price * shares_sold - cost_basis
        log = {
            "Date": self.today,
            "Ticker": ticker,
            "Shares Bought": "",
            "Buy Price": "",
            "Cost Basis": cost_basis,
            "PnL": pnl,
            "Reason": f"MANUAL SELL - {reason}",
            "Shares Sold": shares_sold,
            "Sell Price": sell_price,
        }
        file = "Scripts and CSV Files/chatgpt_trade_log.csv"
        if os.path.exists(file):
            df = pd.read_csv(file)
            df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
        else:
            df = pd.DataFrame([log])
        df.to_csv(file, index=False)
        try:
            from dashboard.audit import record_change
            record_change("manual", "trade_sell", log)
        except Exception:
            pass

        if total_shares == shares_sold:
            chatgpt_portfolio = chatgpt_portfolio[chatgpt_portfolio["ticker"] != ticker]
        else:
            chatgpt_portfolio.loc[chatgpt_portfolio["ticker"] == ticker, "shares"] = (
                total_shares - shares_sold
            )
            chatgpt_portfolio.loc[chatgpt_portfolio["ticker"] == ticker, "cost_basis"] = (
                chatgpt_portfolio.loc[chatgpt_portfolio["ticker"] == ticker, "shares"]
                * buy_price
            )

        cash = cash + shares_sold * sell_price
        send_notification(
            f"Sold {shares_sold} shares of {ticker} at {sell_price} (PnL: {pnl:.2f})."
        )
        return cash, chatgpt_portfolio

    def paper_buy(self, ticker: str, qty: int, order_type: str = "market"):
        """Place a paper buy order through the broker API."""
        return place_order(ticker, qty, "buy", order_type)

    def paper_sell(self, ticker: str, qty: int, order_type: str = "market"):
        """Place a paper sell order through the broker API."""
        return place_order(ticker, qty, "sell", order_type)

