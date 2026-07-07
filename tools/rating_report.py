"""
Aggregate Venti's structured log lines into the beta scorecard.

The server stores NO database by design (build spec: "no database until
the beta proves we need one") — every vent/rating/save emits one
structured log line, and Railway's log stream is the analytics system.
This script is the query interface: feed it one or more exported log
files and it prints the numbers the beta success criteria are judged on.

Usage:
    python tools/rating_report.py railway-export.json [more-files...]
    railway logs --json | python tools/rating_report.py -

Accepts both line formats:
  - Railway log export: {"message": ..., "attributes": {<our fields>}, ...}
  - Raw stdout lines from web.app.main.JsonLogFormatter: {<our fields>}

Exports overlap when taken regularly (do take them regularly — log
retention is 7 days on Railway Hobby, 30 on Pro, and the beta window is
14 days); exact-duplicate records are deduplicated automatically.

Privacy: by construction the inputs contain no vent text, no tokens, and
no user identity — that's enforced server-side by the privacy tests.
Criterion 1 (return rate) is deliberately NOT derivable from logs: there
is no user identity to join on. It comes from personal follow-ups.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict


def parse_records(lines):
    """(records, n_duplicates) from mixed-format JSON log lines.
    Non-JSON and event-less lines are skipped; exact duplicates
    (same fields, same ts — overlapping exports) are dropped."""
    records = []
    seen = set()
    duplicates = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        attrs = obj["attributes"] if isinstance(obj.get("attributes"), dict) else obj
        if not isinstance(attrs.get("event"), str):
            continue
        key = json.dumps(attrs, sort_keys=True, default=str)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        records.append(attrs)
    return records, duplicates


def build_report(records, duplicates=0):
    """The beta scorecard as printable text."""
    by_event = defaultdict(list)
    for r in records:
        by_event[r["event"]].append(r)

    vents = by_event.get("vent", [])
    ratings = [r for r in by_event.get("rating", [])
               if isinstance(r.get("rating"), int)]
    saves = by_event.get("playlist_created", [])
    crises = by_event.get("crisis_declined", [])

    timestamps = sorted(str(r["ts"]) for r in records if r.get("ts"))
    lines = ["# Venti beta scorecard", ""]
    if timestamps:
        lines.append(f"window: {timestamps[0]} → {timestamps[-1]}")
    lines.append(
        f"records: {len(records)}"
        + (f" ({duplicates} duplicate lines skipped)" if duplicates else "")
    )
    lines.append("")

    lines.append(f"vents (sessions): {len(vents)}")
    latencies = [v["latency_ms"] for v in vents
                 if isinstance(v.get("latency_ms"), (int, float))]
    if latencies:
        lines.append(f"  mean latency: {sum(latencies) / len(latencies):.0f} ms")
    lines.append(f"saves: {len(saves)}"
                 + (f" ({len(saves) / len(vents):.0%} of vents)" if vents else ""))
    lines.append(f"crisis declines: {len(crises)}")
    lines.append("")

    lines.append(f"ratings: {len(ratings)}"
                 + (f" ({len(ratings) / len(vents):.0%} of vents)" if vents else ""))
    if ratings:
        mean = sum(r["rating"] for r in ratings) / len(ratings)
        lines.append(f"  mean: {mean:+.2f}")
        dist = Counter(r["rating"] for r in ratings)
        lines.append("  distribution: "
                     + "  ".join(f"[{v:+d}]×{dist.get(v, 0)}" for v in range(-2, 3)))
        by_strategy = defaultdict(list)
        for r in ratings:
            by_strategy[str(r.get("strategy", "?"))].append(r["rating"])
        lines.append("  by strategy:")
        for strategy in sorted(by_strategy):
            scores = by_strategy[strategy]
            lines.append(
                f"    {strategy:<16} n={len(scores):<3} "
                f"mean={sum(scores) / len(scores):+.2f}"
            )
        met = len(ratings) >= 30 and mean > 0.5
        lines.append("")
        lines.append(
            "criterion 2 (mean > +0.5 across ≥30 rated sessions): "
            + ("MET ✅" if met else f"not yet (n={len(ratings)}, mean={mean:+.2f})")
        )
    else:
        lines.append("criterion 2: no ratings recorded yet")

    lines.append("criterion 1 (return rate): not derivable from logs — no user "
                 "identity by design; measure via personal follow-ups")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate Venti log exports into the beta scorecard."
    )
    parser.add_argument(
        "files", nargs="+",
        help="log export files (JSON lines); '-' reads stdin",
    )
    args = parser.parse_args()

    lines = []
    for name in args.files:
        if name == "-":
            lines.extend(sys.stdin.read().splitlines())
        else:
            with open(name, encoding="utf-8") as f:
                lines.extend(f.read().splitlines())

    records, duplicates = parse_records(lines)
    print(build_report(records, duplicates))


if __name__ == "__main__":
    main()
