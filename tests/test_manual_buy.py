import pandas as pd
import pytest
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from src import portfolio as portfolio_module
from src.portfolio import Portfolio
import dashboard.audit as audit_module
import json


def test_log_manual_buy_creates_entry(tmp_path, monkeypatch):
    portfolio_obj = Portfolio(today="2025-08-05")

    # Dummy data instead of real network call
    monkeypatch.setattr(portfolio_module.yf, "download", lambda *a, **k: pd.DataFrame({"Close": [10.0]}))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "0")

    work = tmp_path / "buy"
    work.mkdir()
    (work / "Scripts and CSV Files").mkdir()
    monkeypatch.chdir(work)
    audit_file = work / "audit.log"
    audit_file.write_text("")
    monkeypatch.setattr(audit_module, "LOG_FILE", audit_file)

    cash, pf = portfolio_obj.log_manual_buy(
        buy_price=10.0,
        shares=5,
        ticker="AAA",
        cash=100.0,
        stoploss=5.0,
        chatgpt_portfolio=pd.DataFrame(),
    )

    df = pd.read_csv("Scripts and CSV Files/chatgpt_trade_log.csv")
    assert len(df) == 1
    row = df.iloc[0]
    assert row["Ticker"] == "AAA"
    assert row["Buy Price"] == 10.0
    assert row["Shares Bought"] == 5
    assert cash == pytest.approx(50.0)
    assert pf.iloc[0]["ticker"] == "AAA"
    assert int(pf.iloc[0]["shares"]) == 5
    entries = [json.loads(l) for l in audit_file.read_text().splitlines() if l]
    assert entries[-1]["action"] == "trade_buy"

