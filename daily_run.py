import argparse
import time

from src import trading

try:
    import schedule
except ImportError as exc:  # pragma: no cover - runtime import guard
    raise ImportError(
        "Missing optional dependency 'schedule'.\n"
        "Install it with 'pip install schedule' or 'pip install -r requirements.txt'."
    ) from exc


def run_trading_script(portfolio: str, cash: float) -> None:
    """Execute trading logic for ``portfolio`` using ``cash``."""
    trading.run(portfolio, cash, "config.yaml")


def build_daily_scheduler(
    portfolio: str, cash: float, run_time: str = "09:00"
) -> schedule.Scheduler:
    """Return a scheduler that runs the trading script every day."""
    sched = schedule.Scheduler()
    sched.every().day.at(run_time).do(run_trading_script, portfolio, cash)
    return sched


def run_scheduler(sched: schedule.Scheduler, *, once: bool = False) -> None:
    """Run the scheduler either once or continuously."""
    if once:
        sched.run_all(delay_seconds=0)
        return

    while True:
        sched.run_pending()
        time.sleep(60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run daily trading script")
    parser.add_argument("--portfolio", required=True, help="Portfolio CSV path")
    parser.add_argument("--cash", required=True, type=float, help="Starting cash")
    parser.add_argument("--time", default="09:00", help="HH:MM time for run")

    args = parser.parse_args()

    scheduler = build_daily_scheduler(args.portfolio, args.cash, args.time)
    run_scheduler(scheduler)


if __name__ == "__main__":
    main()
