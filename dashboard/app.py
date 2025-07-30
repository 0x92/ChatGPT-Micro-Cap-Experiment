from flask import Flask, send_file, render_template, url_for, jsonify, request, redirect
import pandas as pd
import yaml
from dotenv import dotenv_values
from pathlib import Path

from src import bot_status
from src.generate_graph import generate_graph

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BASE_DIR / "Scripts and CSV Files"
GRAPH_DIR = BASE_DIR / "graphs"
BOT_STATUS_FILE = BASE_DIR / "bot_status.json"
CONFIG_FILE = BASE_DIR / "config.yaml"
ENV_FILE = BASE_DIR / ".env"

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
app = Flask(__name__, template_folder=TEMPLATE_DIR)


@app.route("/")
def show_portfolio():
    file_path = CSV_DIR / "chatgpt_portfolio_update.csv"
    if not file_path.exists():
        return "Portfolio file not found", 404
    df = pd.read_csv(file_path)
    table = df.to_html(index=False, classes="table table-striped")
    return render_template("portfolio.html", table=table)

@app.route("/log")
def show_log():
    file_candidates = [BASE_DIR / "chatgpt_trade_log.csv", CSV_DIR / "chatgpt_trade_log.csv"]
    file_path = next((p for p in file_candidates if p.exists()), None)
    if not file_path:
        return "Trade log not found", 404
    df = pd.read_csv(file_path)
    table = df.to_html(index=False, classes="table table-striped")
    return render_template("log.html", table=table)

@app.route("/graph_image")
def graph_image():
    GRAPH_DIR.mkdir(exist_ok=True)
    png_files = list(GRAPH_DIR.glob("*.png"))
    if png_files:
        latest = max(png_files, key=lambda p: p.stat().st_mtime)
    else:
        latest = GRAPH_DIR / "performance.png"
        generate_graph(latest.as_posix(), show=False)
    return send_file(latest, mimetype="image/png")


@app.route("/graph")
def show_graph():
    return render_template("graph.html")


@app.route("/summary")
def show_summary():
    file_path = CSV_DIR / "chatgpt_portfolio_update.csv"
    if not file_path.exists():
        return "Portfolio file not found", 404
    df = pd.read_csv(file_path)
    totals = df[df["Ticker"] == "TOTAL"]
    if totals.empty:
        return "No summary data", 404
    latest = totals.iloc[-1]
    return render_template(
        "summary.html",
        date=latest["Date"],
        total=latest["Total Value"],
        pnl=latest["PnL"],
        cash=latest["Cash Balance"],
        equity=latest["Total Equity"],
    )


@app.route("/overview")
def overview():
    """Display graph and summary together."""
    file_path = CSV_DIR / "chatgpt_portfolio_update.csv"
    if not file_path.exists():
        return "Portfolio file not found", 404
    df = pd.read_csv(file_path)
    totals = df[df["Ticker"] == "TOTAL"]
    if totals.empty:
        return "No summary data", 404
    latest = totals.iloc[-1]
    return render_template(
        "overview.html",
        date=latest["Date"],
        total=latest["Total Value"],
        pnl=latest["PnL"],
        cash=latest["Cash Balance"],
        equity=latest["Total Equity"],
    )


@app.route("/config", methods=["GET", "POST"])
def config_page():
    """Display and update configuration settings."""
    if request.method == "POST":
        form = request.form
        try:
            default_cash = float(form.get("default_cash", ""))
            default_stop = float(form.get("default_stop_loss", ""))
        except ValueError:
            return "Invalid numeric values", 400

        tickers_raw = form.get("extra_tickers", "")
        tickers = [t.strip() for t in tickers_raw.split(",") if t.strip()]

        config_data = {
            "default_cash": default_cash,
            "default_stop_loss": default_stop,
            "extra_tickers": tickers,
            "email": form.get("email", ""),
            "webhook_url": form.get("webhook_url", ""),
        }
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(config_data, f)

        env_vals = dotenv_values(ENV_FILE)
        env_vals["BROKER_API_KEY"] = form.get("BROKER_API_KEY", "")
        env_vals["BROKER_SECRET_KEY"] = form.get("BROKER_SECRET_KEY", "")
        env_vals["BROKER_BASE_URL"] = form.get("BROKER_BASE_URL", "")
        with open(ENV_FILE, "w") as f:
            for k, v in env_vals.items():
                f.write(f"{k}={v}\n")

        return redirect(url_for("config_page"))

    cfg = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            cfg = yaml.safe_load(f) or {}
    env = dotenv_values(ENV_FILE)
    return render_template("config.html", config=cfg, env=env)


@app.route("/status")
def show_status():
    """Display live account status."""
    status = bot_status.get_status(BOT_STATUS_FILE)
    if request.args.get("json"):
        return jsonify(status)
    return render_template("status.html", status=status)

if __name__ == "__main__":
    app.run(debug=True)
