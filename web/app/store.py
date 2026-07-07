"""
SQLite event store — the durable home for the beta's analytics (T5.10).

Owner decision (2026-07-07) superseding the "no database" hold-the-line:
Railway log retention (7 days on Hobby) is shorter than the 14-day beta
window, so ratings need real persistence. This module stores WHAT THE
SYSTEM DID — events, strategies, scores, counts, latencies — and by
construction cannot store what a person wrote: the schema has no
free-text columns, and the privacy tests pin that. The frontend's
"nothing you write here is stored" remains literally true.

Deployment: set DATABASE_PATH to a file on a Railway Volume (e.g.
/data/venti.db). Locally it defaults to data/venti.db (gitignored).
Without a volume the file is wiped on every redeploy.

Writes are best-effort by contract: record_event() never raises — a
database hiccup must never break a vent.
"""
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("venti.web.store")

DEFAULT_PATH = "data/venti.db"

_ALLOWED_EVENTS = ("vent", "rating", "playlist_created", "crisis_declined")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    event      TEXT NOT NULL CHECK (event IN
                ('vent', 'rating', 'playlist_created', 'crisis_declined')),
    strategy   TEXT,
    rating     INTEGER CHECK (rating BETWEEN -2 AND 2),
    n_tracks   INTEGER,
    latency_ms INTEGER
)
"""


def db_path() -> str:
    """Read at call time (not import) so tests and deploys can repoint it."""
    return os.environ.get("DATABASE_PATH", DEFAULT_PATH)


def record_event(
    event: str,
    *,
    strategy: str | None = None,
    rating: int | None = None,
    n_tracks: int | None = None,
    latency_ms: int | None = None,
) -> None:
    """Persist one event row. Best-effort: logs db_write_failed (class name
    only) instead of raising — analytics must never break the product."""
    try:
        if event not in _ALLOWED_EVENTS:
            raise ValueError(f"unknown event type: {event!r}")
        path = db_path()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with sqlite3.connect(path, timeout=5) as conn:
            conn.execute(_SCHEMA)
            conn.execute(
                "INSERT INTO events (ts, event, strategy, rating, n_tracks, latency_ms)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (ts, event, strategy, rating, n_tracks, latency_ms),
            )
    except Exception as exc:
        log.warning("db_write_failed", extra={"error_type": type(exc).__name__})


def export_events() -> list[dict]:
    """Every stored event as a dict, oldest first — the payload behind
    GET /api/admin/export, and directly digestible by tools/rating_report."""
    path = db_path()
    if not Path(path).exists():
        return []
    with sqlite3.connect(path, timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM events ORDER BY id").fetchall()
    return [dict(row) for row in rows]
