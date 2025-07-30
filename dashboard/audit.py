import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "audit.log"


def record_change(user: str, action: str, details):
    """Append an audit entry as a JSON line."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user,
        "action": action,
        "details": details,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
