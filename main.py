"""Project entry point that launches all core modules."""
from __future__ import annotations

from threading import Thread

from src import trading
from dashboard.app import app as dashboard_app


DEFAULT_PORTFOLIO = "Scripts and CSV Files/chatgpt_portfolio_update.csv"


def _start_scheduler() -> None:
    """Run the daily scheduler in a background thread."""
    dashboard_app.start_scheduler()


def main() -> None:
    """Launch trading, scheduler and dashboard without CLI args."""
    trading.run(DEFAULT_PORTFOLIO, None, "config.yaml")

    # Start scheduler in a daemon thread so the dashboard can continue serving
    Thread(target=_start_scheduler, daemon=True).start()

    dashboard_app.run(host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
