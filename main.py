"""Command line entry point for project utilities."""
from __future__ import annotations

import argparse

from src import trading
from dashboard.app import app as dashboard_app
import daily_run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Project command line interface")
    sub = parser.add_subparsers(dest="command", required=True)

    dash_p = sub.add_parser("dashboard", help="Run the dashboard server")
    dash_p.add_argument("--host", default="127.0.0.1")
    dash_p.add_argument("--port", type=int, default=5000)

    trade_p = sub.add_parser("trade", help="Run trading script once")
    trade_p.add_argument("--portfolio", required=True)
    trade_p.add_argument("--cash", type=float)
    trade_p.add_argument("--config", default="config.yaml")

    sched_p = sub.add_parser("schedule", help="Run daily scheduler")
    sched_p.add_argument("--portfolio", required=True)
    sched_p.add_argument("--cash", required=True, type=float)
    sched_p.add_argument("--time", default="09:00")

    args = parser.parse_args(argv)

    if args.command == "dashboard":
        dashboard_app.run(host=args.host, port=args.port)
    elif args.command == "trade":
        trading.run(args.portfolio, args.cash, args.config)
    elif args.command == "schedule":
        sched = daily_run.build_daily_scheduler(args.portfolio, args.cash, args.time)
        daily_run.run_scheduler(sched)


if __name__ == "__main__":
    main()
