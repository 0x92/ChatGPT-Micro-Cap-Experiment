import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import dashboard.app as app_module

app = app_module.app


def _setup_files(tmp_path):
    csv_dir = tmp_path / "Scripts and CSV Files"
    csv_dir.mkdir(parents=True)
    graph_dir = tmp_path / "graphs"
    graph_dir.mkdir()

    pf = csv_dir / "chatgpt_portfolio_update.csv"
    pf.write_text("Date,Ticker,Total Value,PnL,Cash Balance,Total Equity\n"
                  "2025-08-10,TOTAL,100,0,100,200\n")

    log = csv_dir / "chatgpt_trade_log.csv"
    log.write_text("Date,Ticker,Shares Bought,Buy Price,Cost Basis,PnL,Reason,Shares Sold,Sell Price\n")

    img = graph_dir / "perf.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    return csv_dir, graph_dir


def test_dashboard_routes(tmp_path, monkeypatch):
    csv_dir, graph_dir = _setup_files(tmp_path)
    monkeypatch.setattr(app_module, "CSV_DIR", csv_dir)
    monkeypatch.setattr(app_module, "GRAPH_DIR", graph_dir)

    with app.test_client() as client:
        assert client.get("/").status_code == 200
        assert client.get("/log").status_code == 200
        assert client.get("/summary").status_code == 200
        assert client.get("/graph_image").status_code == 200
        assert client.get("/overview").status_code == 200


def test_status_route(tmp_path, monkeypatch):
    csv_dir, graph_dir = _setup_files(tmp_path)
    monkeypatch.setattr(app_module, "CSV_DIR", csv_dir)
    monkeypatch.setattr(app_module, "GRAPH_DIR", graph_dir)
    monkeypatch.setattr(app_module, "BOT_STATUS_FILE", tmp_path / "bot_status.json")

    def fake_status(file=None):
        return {
            "timestamp": "now",
            "equity": 100,
            "positions": [],
            "orders": [],
            "last_action": "test",
        }

    monkeypatch.setattr(app_module.bot_status, "get_status", fake_status)

    with app.test_client() as client:
        assert client.get("/status").status_code == 200
        resp = client.get("/status?json=1")
        assert resp.is_json
        assert resp.get_json()["equity"] == 100


