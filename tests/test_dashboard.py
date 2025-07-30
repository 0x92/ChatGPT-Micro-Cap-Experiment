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


def test_config_route_get_post(tmp_path, monkeypatch):
    csv_dir, graph_dir = _setup_files(tmp_path)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("default_cash: 50\ndefault_stop_loss: 0.1\nextra_tickers:\n- AAA\n")
    env_file = tmp_path / ".env"
    env_file.write_text("BROKER_API_KEY=old\n")

    monkeypatch.setattr(app_module, "CSV_DIR", csv_dir)
    monkeypatch.setattr(app_module, "GRAPH_DIR", graph_dir)
    monkeypatch.setattr(app_module, "CONFIG_FILE", cfg_file)
    monkeypatch.setattr(app_module, "ENV_FILE", env_file)

    with app.test_client() as client:
        resp = client.get("/config")
        assert resp.status_code == 200

        resp = client.post(
            "/config",
            data={
                "default_cash": "75",
                "default_stop_loss": "0.2",
                "extra_tickers": "BBB,CCC",
                "BROKER_API_KEY": "newkey",
                "BROKER_SECRET_KEY": "secret",
                "BROKER_BASE_URL": "http://example.com",
            },
        )
        assert resp.status_code == 302

    import yaml
    from dotenv import dotenv_values

    cfg = yaml.safe_load(cfg_file.read_text())
    assert cfg["default_cash"] == 75.0
    assert cfg["default_stop_loss"] == 0.2
    assert cfg["extra_tickers"] == ["BBB", "CCC"]

    env_vals = dotenv_values(env_file)
    assert env_vals["BROKER_API_KEY"] == "newkey"
    assert env_vals["BROKER_SECRET_KEY"] == "secret"
    assert env_vals["BROKER_BASE_URL"] == "http://example.com"


def test_scheduler_route(tmp_path, monkeypatch):
    csv_dir, graph_dir = _setup_files(tmp_path)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("")

    monkeypatch.setattr(app_module, "CSV_DIR", csv_dir)
    monkeypatch.setattr(app_module, "GRAPH_DIR", graph_dir)
    monkeypatch.setattr(app_module, "CONFIG_FILE", cfg_file)

    started = {}

    def fake_restart(time):
        started["time"] = time

    monkeypatch.setattr(app_module, "restart_scheduler", fake_restart)

    with app.test_client() as client:
        resp = client.post("/scheduler", data={"run_time": "10:30"})
        assert resp.status_code == 302

    import yaml

    cfg = yaml.safe_load(cfg_file.read_text())
    assert cfg["run_time"] == "10:30"
    assert started["time"] == "10:30"


