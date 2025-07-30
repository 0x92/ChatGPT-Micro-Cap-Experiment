from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from . import broker

# Default location for the status json file relative to repo root
STATUS_FILE = Path(__file__).resolve().parents[1] / "bot_status.json"


def _read_last_action(file: Path = STATUS_FILE) -> str | None:
    """Return the last recorded action from ``file`` if present."""
    if file.exists():
        try:
            with file.open() as f:
                data = json.load(f)
            return data.get("last_action")
        except Exception:
            return None
    return None


def get_status(status_file: Path = STATUS_FILE) -> Dict[str, Any]:
    """Return latest account status information.

    Parameters
    ----------
    status_file:
        Path to the json file storing the last action note.

    Returns
    -------
    Dict[str, Any]
        Dictionary with keys ``timestamp``, ``equity``, ``positions``,
        ``orders`` and ``last_action``.
    """
    account = broker.get_account()
    equity = account.get("equity")
    positions = broker.list_positions()
    orders = broker.list_orders(status="open")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "equity": equity,
        "positions": positions,
        "orders": orders,
        "last_action": _read_last_action(status_file),
    }
