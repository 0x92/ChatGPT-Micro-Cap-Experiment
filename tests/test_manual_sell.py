import pandas as pd
import pytest
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from src.portfolio import Portfolio


def test_log_manual_sell_updates_portfolio(tmp_path, monkeypatch):
    portfolio_obj = Portfolio(today="2025-08-06")
    monkeypatch.setattr("builtins.input", lambda *a, **k: "profit")

    work = tmp_path / "sell"
    work.mkdir()
    (work / "Scripts and CSV Files").mkdir()
    monkeypatch.chdir(work)

    portfolio = pd.DataFrame([
        {"ticker": "AAA", "shares": 10, "stop_loss": 0.0, "buy_price": 2.0, "cost_basis": 20.0}
    ])

    cash, updated = portfolio_obj.log_manual_sell(3.0, 5, "AAA", 100.0, portfolio)

    df = pd.read_csv("Scripts and CSV Files/chatgpt_trade_log.csv")
    assert len(df) == 1
    row = df.iloc[0]
    assert row["Ticker"] == "AAA"
    assert row["Shares Sold"] == 5
    assert cash == pytest.approx(115.0)
    assert int(updated.iloc[0]["shares"]) == 5
    assert updated.iloc[0]["cost_basis"] == pytest.approx(10.0)


def test_log_manual_sell_too_many_shares(tmp_path, monkeypatch):
    portfolio_obj = Portfolio(today="2025-08-07")
    monkeypatch.setattr("builtins.input", lambda *a, **k: "profit")

    work = tmp_path / "fail"
    work.mkdir()
    (work / "Scripts and CSV Files").mkdir()
    monkeypatch.chdir(work)

    portfolio = pd.DataFrame([
        {"ticker": "AAA", "shares": 4, "stop_loss": 0.0, "buy_price": 2.0, "cost_basis": 8.0}
    ])

    with pytest.raises(ValueError):
        portfolio_obj.log_manual_sell(3.0, 5, "AAA", 100.0, portfolio)
