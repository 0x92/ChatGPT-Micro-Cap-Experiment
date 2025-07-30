import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import daily_run


def test_run_scheduler_invokes_job(monkeypatch):
    called = {}

    def fake_run(portfolio, cash):
        called['args'] = (portfolio, cash)

    monkeypatch.setattr(daily_run, 'run_trading_script', fake_run)
    sched = daily_run.build_daily_scheduler('pf.csv', 50.0, run_time='00:00')
    daily_run.run_scheduler(sched, once=True)

    assert called['args'] == ('pf.csv', 50.0)
