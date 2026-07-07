"""
tools/rating_report.py — the offline scorecard over exported log lines.
Covers both input formats (Railway export + raw JsonLogFormatter stdout),
duplicate-export dedup, the aggregate math, and the criterion-2 gate.
"""
import json

from tools.rating_report import build_report, parse_records


def _railway(attrs):
    """A line as Railway's log export wraps it."""
    return json.dumps({
        "message": "",
        "severity": "info",
        "attributes": attrs,
        "tags": {"project": "p", "deployment": "d"},
        "timestamp": attrs.get("ts", ""),
    })


def _raw(attrs):
    """A line as JsonLogFormatter writes it to stdout."""
    return json.dumps(attrs)


def _rating(ts, strategy, score):
    return {"ts": ts, "level": "info", "logger": "venti.web.rating",
            "event": "rating", "strategy": strategy, "rating": score}


def _vent(ts, strategy, latency_ms=1200):
    return {"ts": ts, "level": "info", "logger": "venti.web.vent",
            "event": "vent", "strategy": strategy, "n_tracks": 4,
            "latency_ms": latency_ms}


def test_parses_both_formats_and_skips_junk():
    lines = [
        _railway(_vent("2026-07-07T10:00:00+00:00", "discharge")),
        _raw(_rating("2026-07-07T10:05:00+00:00", "discharge", 2)),
        "not json at all",
        json.dumps(["a", "list"]),
        json.dumps({"no_event": True}),
        "",
    ]
    records, duplicates = parse_records(lines)
    assert [r["event"] for r in records] == ["vent", "rating"]
    assert duplicates == 0


def test_overlapping_exports_deduplicate():
    rating = _rating("2026-07-07T10:05:00+00:00", "solace", 1)
    week1 = [_railway(rating)]
    week2 = [_railway(rating),  # same event exported twice
             _railway(_rating("2026-07-08T09:00:00+00:00", "solace", 2))]
    records, duplicates = parse_records(week1 + week2)
    assert len(records) == 2
    assert duplicates == 1


def test_report_math_and_strategy_breakdown():
    lines = [
        _raw(_vent("t1", "discharge")),
        _raw(_vent("t2", "solace")),
        _raw(_rating("t3", "discharge", 2)),
        _raw(_rating("t4", "discharge", 0)),
        _raw(_rating("t5", "solace", -1)),
        _raw({"ts": "t6", "event": "playlist_created", "n_tracks": 4}),
        _raw({"ts": "t7", "event": "crisis_declined"}),
    ]
    records, _ = parse_records(lines)
    report = build_report(records)
    assert "vents (sessions): 2" in report
    assert "ratings: 3" in report
    assert "mean: +0.33" in report
    assert "crisis declines: 1" in report
    assert "saves: 1" in report
    assert "discharge" in report and "n=2" in report and "mean=+1.00" in report
    assert "solace" in report and "mean=-1.00" in report
    # 3 ratings is below the ≥30 gate regardless of mean.
    assert "not yet (n=3" in report


def test_criterion_2_gate():
    good = [_raw(_rating(f"t{i}", "solace", 1)) for i in range(30)]
    records, _ = parse_records(good)
    assert "MET ✅" in build_report(records)

    # 30 ratings but mean exactly +0.5 is NOT strictly greater — not met.
    half = [_raw(_rating(f"a{i}", "solace", 1)) for i in range(15)]
    half += [_raw(_rating(f"b{i}", "solace", 0)) for i in range(15)]
    records, _ = parse_records(half)
    assert "not yet (n=30, mean=+0.50)" in build_report(records)


def test_no_ratings_yet():
    records, _ = parse_records([_raw(_vent("t1", "revival"))])
    report = build_report(records)
    assert "criterion 2: no ratings recorded yet" in report
    assert "return rate" in report  # criterion 1 caveat always present
