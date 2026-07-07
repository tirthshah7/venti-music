"""
T5.10 event store: schema is metadata-only by construction, writes are
best-effort (never raise), export round-trips into tools/rating_report.
"""
import logging
import sqlite3

from tools.rating_report import build_report, parse_records
from web.app import store


def test_record_and_export_roundtrip():
    store.record_event("vent", strategy="discharge", n_tracks=4, latency_ms=980)
    store.record_event("rating", strategy="discharge", rating=2)
    store.record_event("crisis_declined")

    events = store.export_events()
    assert [e["event"] for e in events] == ["vent", "rating", "crisis_declined"]
    vent, rating, crisis = events
    assert vent["strategy"] == "discharge" and vent["n_tracks"] == 4
    assert rating["rating"] == 2
    # Crisis rows carry the timestamp and nothing else (T5.1 discipline).
    assert crisis["strategy"] is None
    assert crisis["rating"] is None
    assert all(e["ts"] for e in events)


def test_schema_has_no_text_capable_columns_beyond_enums():
    # The privacy promise, structurally: the only TEXT columns are ts,
    # event (CHECK-constrained), and strategy (validated upstream against
    # the MMR enum). No column exists that could hold a vent.
    store.record_event("vent", strategy="solace")
    with sqlite3.connect(store.db_path()) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
    assert columns == {"id", "ts", "event", "strategy", "rating", "n_tracks", "latency_ms"}


def test_unknown_event_rejected_without_raising(caplog):
    with caplog.at_level(logging.WARNING):
        store.record_event("vent_text_dump")  # not in the allowlist
    assert store.export_events() == []
    failed = next(r for r in caplog.records if r.getMessage() == "db_write_failed")
    assert failed.error_type == "ValueError"


def test_db_failure_never_raises(monkeypatch, tmp_path, caplog):
    # Point the DB somewhere unwritable: parent "path" is a file.
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory")
    monkeypatch.setenv("DATABASE_PATH", str(blocker / "venti.db"))
    with caplog.at_level(logging.WARNING):
        store.record_event("rating", strategy="solace", rating=1)  # must not raise
    assert any(r.getMessage() == "db_write_failed" for r in caplog.records)


def test_export_feeds_rating_report_directly():
    import json

    for score in (2, 1, 0):
        store.record_event("rating", strategy="revival", rating=score)
    lines = [json.dumps(e) for e in store.export_events()]
    records, duplicates = parse_records(lines)
    assert len(records) == 3 and duplicates == 0
    report = build_report(records)
    assert "ratings: 3" in report
    assert "mean: +1.00" in report
    assert "revival" in report
