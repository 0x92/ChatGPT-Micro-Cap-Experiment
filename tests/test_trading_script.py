import types
import pandas as pd
import pathlib
import builtins

import pytest


# Helper to load the trading script without executing the bottom example code
def load_trading_module():
    path = pathlib.Path(__file__).resolve().parents[1] / "Scripts and CSV Files" / "Trading_Script.py"
    text = path.read_text()
    # Strip off the example execution section
    text = text.split("# === Run Portfolio ===")[0]
    module = types.ModuleType("trading_script")
    exec(text, module.__dict__)
    return module

def test_process_portfolio_total_equity(tmp_path, monkeypatch):
    module = load_trading_module()
    module.today = "2025-08-01"

    # Fake yfinance history data
    prices = {"AAA": 6.0, "BBB": 3.0}

    class DummyTicker:
        def __init__(self, ticker):
            self.ticker = ticker
        def history(self, period="1d"):
            return pd.DataFrame({"Close": [prices[self.ticker]]})

    monkeypatch.setattr(module.yf, "Ticker", DummyTicker)
    # Avoid writing trade logs
    monkeypatch.setattr(module, "log_sell", lambda *a, **k: None)

    # Prepare working directory
    work = tmp_path / "run"
    work.mkdir()
    (work / "Scripts and CSV Files").mkdir()
    monkeypatch.chdir(work)

    portfolio = pd.DataFrame([
        {"ticker": "AAA", "shares": 10, "stop_loss": 5.0, "buy_price": 5.0},
        {"ticker": "BBB", "shares": 5, "stop_loss": 2.0, "buy_price": 2.5},
    ])

    result_path = module.process_portfolio(portfolio, 100.0)
    df = pd.read_csv(result_path)
    total_row = df[df["Ticker"] == "TOTAL"].iloc[-1]
    assert total_row["Total Equity"] == pytest.approx(175.0)

def test_log_sell_appends(tmp_path, monkeypatch):
    module = load_trading_module()
    module.today = "2025-08-02"

    work = tmp_path / "log"
    work.mkdir()
    (work / "Scripts and CSV Files").mkdir()
    monkeypatch.chdir(work)

    # First call creates the file
    module.log_sell("AAA", 1, 6.0, 5.0, 1.0)
    df = pd.read_csv("Scripts and CSV Files/chatgpt_trade_log.csv")
    assert len(df) == 1
    first_date = df.iloc[0]["Date"]

    # Second call appends
    module.log_sell("BBB", 2, 3.0, 2.0, 2.0)
    df2 = pd.read_csv("Scripts and CSV Files/chatgpt_trade_log.csv")
    assert len(df2) == 2
    assert df2.iloc[-1]["Ticker"] == "BBB"
    assert df2.iloc[0]["Date"] == first_date


def test_process_portfolio_skips_empty(tmp_path, monkeypatch, capsys):
    module = load_trading_module()
    module.today = "2025-08-03"

    class DummyTicker:
        def __init__(self, ticker):
            self.ticker = ticker
        def history(self, period="1d"):
            if self.ticker == "AAA":
                return pd.DataFrame()
            return pd.DataFrame({"Close": [3.0]})

    monkeypatch.setattr(module.yf, "Ticker", DummyTicker)
    monkeypatch.setattr(module, "log_sell", lambda *a, **k: None)

    work = tmp_path / "skip"
    work.mkdir()
    (work / "Scripts and CSV Files").mkdir()
    monkeypatch.chdir(work)

    portfolio = pd.DataFrame([
        {"ticker": "AAA", "shares": 10, "stop_loss": 5.0, "buy_price": 5.0},
        {"ticker": "BBB", "shares": 5, "stop_loss": 2.0, "buy_price": 2.5},
    ])

    result_path = module.process_portfolio(portfolio, 100.0)
    out = capsys.readouterr().out

    df = pd.read_csv(result_path)
    assert "AAA" not in df["Ticker"].values
    total_row = df[df["Ticker"] == "TOTAL"].iloc[-1]
    assert total_row["Total Equity"] == pytest.approx(115.0)
    assert "Warning: no price history for AAA" in out
