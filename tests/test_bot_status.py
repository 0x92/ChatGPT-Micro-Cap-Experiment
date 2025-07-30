import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import src.bot_status as bot_status


def test_get_status(monkeypatch, tmp_path):
    monkeypatch.setattr(bot_status, "STATUS_FILE", tmp_path / "status.json")
    monkeypatch.setattr(bot_status.broker, "get_account", lambda: {"equity": "50"})
    monkeypatch.setattr(bot_status.broker, "list_positions", lambda: [{"symbol": "AAA"}])
    monkeypatch.setattr(bot_status.broker, "list_orders", lambda status="open": [{"id": "1"}])
    tmp = bot_status.STATUS_FILE
    # create last action file
    (tmp).write_text('{"last_action": "did"}')

    result = bot_status.get_status(bot_status.STATUS_FILE)
    assert result["equity"] == "50"
    assert result["positions"][0]["symbol"] == "AAA"
    assert result["orders"][0]["id"] == "1"
    assert result["last_action"] == "did"
