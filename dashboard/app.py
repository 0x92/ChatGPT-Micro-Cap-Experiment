from flask import (
    Flask,
    send_file,
    render_template,
    url_for,
    jsonify,
    request,
    redirect,
)
import pandas as pd
import yaml
from dotenv import dotenv_values
from pathlib import Path
from flask_login import login_required
from .auth import auth_bp, login_manager

from threading import Thread, Event
import time
import daily_run
import shutil
import io
from datetime import datetime



from src import bot_status
from src.generate_graph import generate_graph
from src.portfolio import Portfolio
import builtins
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BASE_DIR / "Scripts and CSV Files"
GRAPH_DIR = BASE_DIR / "graphs"
BOT_STATUS_FILE = BASE_DIR / "bot_status.json"
CONFIG_FILE = BASE_DIR / "config.yaml"
ENV_FILE = BASE_DIR / ".env"

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = "devkey"

login_manager.init_app(app)
app.register_blueprint(auth_bp)

# ---- Scheduler Management ----

PORTFOLIO_FILE = CSV_DIR / "chatgpt_portfolio_update.csv"

_scheduler_thread: Thread | None = None
_scheduler_event: Event | None = None


def _scheduler_loop(sched: 'schedule.Scheduler', stop_event: Event) -> None:
    """Run pending jobs until ``stop_event`` is set."""
    while not stop_event.is_set():
        sched.run_pending()
        time.sleep(60)


def start_scheduler(run_time: str | None = None) -> None:
    """Start the daily trading scheduler in a background thread."""
    global _scheduler_thread, _scheduler_event

    if run_time is None:
        run_time = "09:00"
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                cfg = yaml.safe_load(f) or {}
                run_time = cfg.get("run_time", run_time)

    stop_event = Event()
    sched = daily_run.build_daily_scheduler(
        PORTFOLIO_FILE.as_posix(), cash=0.0, run_time=run_time
    )
    thread = Thread(target=_scheduler_loop, args=(sched, stop_event), daemon=True)
    _scheduler_thread = thread
    _scheduler_event = stop_event
    thread.start()


def stop_scheduler() -> None:
    """Stop the running scheduler thread if active."""
    global _scheduler_thread, _scheduler_event
    if _scheduler_thread and _scheduler_event:
        _scheduler_event.set()
        _scheduler_thread.join()
    _scheduler_thread = None
    _scheduler_event = None


def restart_scheduler(run_time: str) -> None:
    """Restart the scheduler thread using ``run_time``."""
    stop_scheduler()
    start_scheduler(run_time)


@app.route("/")
def show_portfolio():
    file_path = CSV_DIR / "chatgpt_portfolio_update.csv"
    if not file_path.exists():
        return "Portfolio file not found", 404
    df = pd.read_csv(file_path)
    table = df.to_html(index=False, classes="table table-striped")
    return render_template("portfolio.html", table=table)


@app.route("/portfolio/edit", methods=["GET", "POST"])
def edit_portfolio():
    """Upload or edit the portfolio CSV."""
    file_path = CSV_DIR / "chatgpt_portfolio_update.csv"
    backups = CSV_DIR / "backups"
    csv_text = None
    if request.method == "POST":
        backups.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if file_path.exists():
            backup = backups / f"chatgpt_portfolio_update_{timestamp}.csv"
            shutil.copy(file_path, backup)

        uploaded = request.files.get("file")
        if uploaded and uploaded.filename:
            df = pd.read_csv(uploaded)
        else:
            csv_text = request.form.get("csv_text", "")
            df = pd.read_csv(io.StringIO(csv_text)) if csv_text.strip() else pd.DataFrame()
        df.to_csv(file_path, index=False)
        csv_text = df.to_csv(index=False)

    if csv_text is None:
        if file_path.exists():
            csv_text = file_path.read_text()
        else:
            csv_text = ""

    df_display = pd.read_csv(io.StringIO(csv_text)) if csv_text.strip() else pd.DataFrame()
    table = df_display.to_html(index=False, classes="table table-striped") if not df_display.empty else ""
    return render_template("portfolio_edit.html", table=table, csv_text=csv_text)

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
@login_required
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


@app.route("/scheduler", methods=["GET", "POST"])
def scheduler_page():
    """View and update the daily scheduler run time."""
    run_time = "09:00"
    cfg = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            cfg = yaml.safe_load(f) or {}
            run_time = cfg.get("run_time", run_time)

    if request.method == "POST":
        run_time = request.form.get("run_time", run_time)
        cfg["run_time"] = run_time
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(cfg, f)
        restart_scheduler(run_time)
        return redirect(url_for("scheduler_page"))

    return render_template("scheduler.html", run_time=run_time)

@app.route("/manual_buy", methods=["GET", "POST"])
def manual_buy():
    """Manually log a buy trade and refresh portfolio CSV."""
    if request.method == "POST":
        form = request.form
        ticker = form.get("ticker", "").upper()
        try:
            shares = int(form.get("shares", "0"))
            price = float(form.get("price", "0"))
            stop = float(form.get("stop_loss", "0"))
        except ValueError:
            return "Invalid numeric values", 400

        pf_file = CSV_DIR / "chatgpt_portfolio_update.csv"
        if not pf_file.exists():
            return "Portfolio file not found", 404
        df = pd.read_csv(pf_file)
        latest_date = df["Date"].max()
        current = df[df["Date"] == latest_date].copy()
        cash = 0.0
        if not current.empty:
            cash_row = current[current["Ticker"] == "TOTAL"]
            if not cash_row.empty:
                cash = float(cash_row["Cash Balance"].iloc[0])
            current = current[current["Ticker"] != "TOTAL"]

        current = current.rename(
            columns={
                "Ticker": "ticker",
                "Shares": "shares",
                "Stop Loss": "stop_loss",
                "Cost Basis": "buy_price",
            }
        )
        if not current.empty:
            current["cost_basis"] = current["buy_price"] * current["shares"]

        portfolio_obj = Portfolio(today=datetime.today().strftime("%Y-%m-%d"))
        old_input = builtins.input
        builtins.input = lambda *a, **k: "0"
        try:
            cash, updated = portfolio_obj.log_manual_buy(
                price,
                shares,
                ticker,
                cash,
                stop,
                current,
            )
        finally:
            builtins.input = old_input

        portfolio_obj.process(updated, cash)
        return redirect(url_for("show_portfolio"))

    return render_template("manual_buy.html")


@app.route("/manual_sell", methods=["GET", "POST"])
def manual_sell():
    """Manually log a sell trade and refresh portfolio CSV."""
    if request.method == "POST":
        form = request.form
        ticker = form.get("ticker", "").upper()
        try:
            shares = int(form.get("shares", "0"))
            price = float(form.get("price", "0"))
        except ValueError:
            return "Invalid numeric values", 400

        pf_file = CSV_DIR / "chatgpt_portfolio_update.csv"
        if not pf_file.exists():
            return "Portfolio file not found", 404
        df = pd.read_csv(pf_file)
        latest_date = df["Date"].max()
        current = df[df["Date"] == latest_date].copy()
        cash = 0.0
        if not current.empty:
            cash_row = current[current["Ticker"] == "TOTAL"]
            if not cash_row.empty:
                cash = float(cash_row["Cash Balance"].iloc[0])
            current = current[current["Ticker"] != "TOTAL"]

        current = current.rename(
            columns={
                "Ticker": "ticker",
                "Shares": "shares",
                "Stop Loss": "stop_loss",
                "Cost Basis": "buy_price",
            }
        )
        if not current.empty:
            current["cost_basis"] = current["buy_price"] * current["shares"]

        portfolio_obj = Portfolio(today=datetime.today().strftime("%Y-%m-%d"))
        old_input = builtins.input
        builtins.input = lambda *a, **k: "web"
        try:
            cash, updated = portfolio_obj.log_manual_sell(
                price,
                shares,
                ticker,
                cash,
                current,
            )
        except (KeyError, ValueError) as exc:
            builtins.input = old_input
            return str(exc), 400
        finally:
            builtins.input = old_input

        portfolio_obj.process(updated, cash)
        return redirect(url_for("show_portfolio"))

    return render_template("manual_sell.html")


@app.route("/status")
def show_status():
    """Display live account status."""
    status = bot_status.get_status(BOT_STATUS_FILE)
    if request.args.get("json"):
        return jsonify(status)
    return render_template("status.html", status=status)


@app.route("/portfolio/edit", methods=["POST"])
@login_required
def edit_portfolio():
    return "Not implemented", 501


@app.route("/manual_buy", methods=["POST"])
@login_required
def manual_buy():
    return "Not implemented", 501


@app.route("/manual_sell", methods=["POST"])
@login_required
def manual_sell():
    return "Not implemented", 501


@app.route("/scheduler", methods=["POST"])
@login_required
def scheduler():
    return "Not implemented", 501

if __name__ == "__main__":
    app.run(debug=True)
