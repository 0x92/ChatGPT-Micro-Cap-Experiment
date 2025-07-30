from flask import Flask, send_file, render_template, url_for, jsonify, request
import pandas as pd
from pathlib import Path
import sys

from src import bot_status

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BASE_DIR / "Scripts and CSV Files"
GRAPH_DIR = BASE_DIR / "graphs"
BOT_STATUS_FILE = BASE_DIR / "bot_status.json"

sys.path.append(str(CSV_DIR))
from Generate_Graph import generate_graph

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


@app.route("/status")
def show_status():
    """Display live account status."""
    status = bot_status.get_status(BOT_STATUS_FILE)
    if request.args.get("json"):
        return jsonify(status)
    return render_template("status.html", status=status)

if __name__ == "__main__":
    app.run(debug=True)
