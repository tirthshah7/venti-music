"""
Pulse introspection tool.

Reads every session JSON in data/sessions/ and produces a human-readable
markdown report covering:
  - Strategy distribution
  - Average rating per strategy (with sample sizes)
  - Average rating by context keyword
  - Recent trend (last 5 vs. earlier sessions)
  - Top positive and top negative session excerpts
  - Suggestions for what to look into next

Usage:
    python tools/introspect.py
    python tools/introspect.py --output report.md
    python tools/introspect.py --since 2026-05-01

This is deliberately small (~250 lines) so contributors can extend it.
Designed to be useful at 5 sessions and increasingly insightful as
sessions accumulate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev


# Common English stopwords — keep this list short and obvious so contributors
# can see exactly what's being filtered and tweak it.
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "doing", "this",
    "that", "these", "those", "i", "me", "my", "we", "us", "our", "you",
    "your", "it", "its", "he", "she", "they", "them", "their", "what",
    "which", "who", "whom", "if", "then", "than", "so", "just", "very",
    "much", "more", "most", "some", "any", "all", "no", "not", "n't",
    "would", "could", "should", "will", "can", "may", "might", "must",
    "about", "into", "through", "during", "before", "after", "above",
    "below", "out", "off", "down", "up", "over", "under", "again", "also",
    "really", "still", "now", "even", "ever", "back", "way", "things",
    "thing", "got", "get", "going", "go", "gone", "feel", "feeling", "felt",
    "like", "want", "make", "made", "take", "took", "see", "seen",
    "saw", "know", "knew", "think", "thought", "well", "good", "bad",
    "lot", "okay", "ok", "yeah", "yes", "uh", "um",
}


def load_sessions(sessions_dir: Path, since: datetime | None = None) -> list[dict]:
    """Load every session JSON, sorted by timestamp ascending."""
    sessions = []
    for path in sorted(sessions_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Skipping {path.name}: {e}", file=sys.stderr)
            continue
        ts = data.get("timestamp", "")
        if since and ts < since.isoformat():
            continue
        sessions.append(data)
    return sessions


def tokenize(text: str) -> list[str]:
    """Crude tokenizer — lowercase, alpha-only words 3+ chars, no stopwords."""
    words = re.findall(r"[a-zA-Z']{3,}", text.lower())
    return [w for w in words if w not in STOPWORDS]


def strategy_distribution(sessions: list[dict]) -> Counter:
    return Counter(s["strategy"] for s in sessions if "strategy" in s)


def rating_by_strategy(sessions: list[dict]) -> dict[str, list[int]]:
    """Group ratings by strategy. Sessions without ratings are skipped."""
    by_strat: dict[str, list[int]] = defaultdict(list)
    for s in sessions:
        rating = s.get("post_session_rating")
        strat = s.get("strategy")
        if rating is not None and strat:
            by_strat[strat].append(rating)
    return dict(by_strat)


def keyword_ratings(sessions: list[dict], min_occurrences: int = 2) -> list[tuple[str, float, int]]:
    """
    For each keyword that appears in at least `min_occurrences` rated sessions,
    return (keyword, mean_rating, n). Sorted by mean rating ascending so
    problem patterns surface first.
    """
    by_word: dict[str, list[int]] = defaultdict(list)
    for s in sessions:
        rating = s.get("post_session_rating")
        if rating is None:
            continue
        text = (s.get("vent_text", "") + " " + s.get("context", "")).strip()
        for token in set(tokenize(text)):  # set() so each word counts once per session
            by_word[token].append(rating)

    rows = [
        (word, mean(ratings), len(ratings))
        for word, ratings in by_word.items()
        if len(ratings) >= min_occurrences
    ]
    rows.sort(key=lambda r: (r[1], -r[2]))
    return rows


def recency_trend(sessions: list[dict], window: int = 5) -> tuple[float | None, float | None]:
    """Compare mean rating in last `window` rated sessions vs. earlier rated sessions."""
    rated = [s for s in sessions if s.get("post_session_rating") is not None]
    if len(rated) < window + 1:
        return (None, None)
    recent = [s["post_session_rating"] for s in rated[-window:]]
    earlier = [s["post_session_rating"] for s in rated[:-window]]
    return (mean(earlier), mean(recent))


def excerpt(session: dict, max_len: int = 80) -> str:
    text = session.get("vent_text", "").replace("\n", " ").strip()
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def top_sessions(sessions: list[dict], positive: bool, n: int = 3) -> list[dict]:
    rated = [s for s in sessions if s.get("post_session_rating") is not None]
    rated.sort(key=lambda s: s["post_session_rating"], reverse=positive)
    return rated[:n]


def format_report(sessions: list[dict]) -> str:
    out: list[str] = []
    w = out.append

    n = len(sessions)
    rated = [s for s in sessions if s.get("post_session_rating") is not None]
    n_rated = len(rated)

    w("# Pulse Session Report")
    w(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    w("")
    w(f"**Total sessions:** {n}  ")
    w(f"**Rated sessions:** {n_rated} ({n_rated / n * 100:.0f}% rated)" if n else "**Rated sessions:** 0")
    if rated:
        all_ratings = [s["post_session_rating"] for s in rated]
        w(f"**Average rating:** {mean(all_ratings):+.2f}")
        if len(all_ratings) > 1:
            w(f"**Rating std dev:** {stdev(all_ratings):.2f}")
    w("")

    if n < 5:
        w("> ⚠️ Fewer than 5 sessions logged. Most stats will be unreliable; the")
        w("> tool is mostly along for the ride until you accumulate more data.")
        w("")

    # ── Strategy distribution ─────────────────────────────────────────────
    w("## Strategy distribution")
    w("")
    dist = strategy_distribution(sessions)
    if dist:
        w("| Strategy | Sessions | Share |")
        w("|---|---:|---:|")
        for strat, count in dist.most_common():
            w(f"| {strat} | {count} | {count / n * 100:.0f}% |")
    else:
        w("_(no strategy data yet)_")
    w("")

    # ── Rating by strategy ────────────────────────────────────────────────
    w("## Average rating by strategy")
    w("")
    by_strat = rating_by_strategy(sessions)
    if by_strat:
        w("| Strategy | Avg rating | N | Range |")
        w("|---|---:|---:|---:|")
        rows = sorted(
            ((strat, mean(rs), len(rs), min(rs), max(rs)) for strat, rs in by_strat.items()),
            key=lambda r: r[1],
            reverse=True,
        )
        for strat, avg, count, lo, hi in rows:
            flag = " ⚠️" if count < 3 else ""
            w(f"| {strat} | {avg:+.2f}{flag} | {count} | {lo:+d} to {hi:+d} |")
        w("")
        w("⚠️ = small sample, treat with skepticism.")
    else:
        w("_(no rated sessions yet — rate some with `vent rate <-2..+2>`)_")
    w("")

    # ── Recency trend ─────────────────────────────────────────────────────
    earlier, recent = recency_trend(sessions, window=5)
    if earlier is not None and recent is not None:
        w("## Recency trend")
        w("")
        delta = recent - earlier
        arrow = "↑" if delta > 0.2 else ("↓" if delta < -0.2 else "→")
        w(f"Last 5 rated sessions: **{recent:+.2f}** average  ")
        w(f"Earlier rated sessions: **{earlier:+.2f}** average  ")
        w(f"Direction: **{arrow} {delta:+.2f}**")
        w("")
        if delta < -0.5:
            w("> 📉 Recent sessions are rating notably worse. Worth a closer look at")
            w("> the negative ones to spot what changed.")
        elif delta > 0.5:
            w("> 📈 Recent sessions are trending up. Either you're using it for")
            w("> contexts that suit it better, or something in your tuning helped.")
        w("")

    # ── Keyword patterns ──────────────────────────────────────────────────
    w("## Context keywords (worst → best)")
    w("")
    rows = keyword_ratings(sessions, min_occurrences=2)
    if rows:
        w("Keywords appearing in 2+ rated sessions, sorted by mean rating.")
        w("Low-rated keywords are where Pulse may be misreading you.")
        w("")
        w("| Keyword | Avg rating | N |")
        w("|---|---:|---:|")
        for word, avg, count in rows[:15]:
            w(f"| `{word}` | {avg:+.2f} | {count} |")
        w("")
        if len(rows) > 15:
            w(f"_(showing 15 of {len(rows)} keywords with ≥2 occurrences)_")
    else:
        w("_(not enough rated sessions for keyword patterns yet — need 2+ rated_")
        w("_sessions sharing at least one non-stopword)_")
    w("")

    # ── Best and worst sessions ───────────────────────────────────────────
    if rated:
        w("## Top-rated sessions")
        w("")
        for s in top_sessions(sessions, positive=True, n=3):
            r = s["post_session_rating"]
            ts = s.get("timestamp", "")[:10]
            strat = s.get("strategy", "?")
            note = s.get("notes") or ""
            w(f"- **{r:+d}** ({ts}, _{strat}_): \"{excerpt(s)}\"")
            if note:
                w(f"  - Note: _{note}_")
        w("")

        w("## Worst-rated sessions")
        w("")
        for s in top_sessions(sessions, positive=False, n=3):
            r = s["post_session_rating"]
            ts = s.get("timestamp", "")[:10]
            strat = s.get("strategy", "?")
            note = s.get("notes") or ""
            w(f"- **{r:+d}** ({ts}, _{strat}_): \"{excerpt(s)}\"")
            if note:
                w(f"  - Note: _{note}_")
        w("")

    # ── Suggestions ───────────────────────────────────────────────────────
    w("## Suggestions")
    w("")
    suggestions = generate_suggestions(sessions, by_strat, rows if rated else [])
    if suggestions:
        for s in suggestions:
            w(f"- {s}")
    else:
        w("- Keep dogfooding. Nothing actionable jumps out yet.")
    w("")

    return "\n".join(out)


def generate_suggestions(
    sessions: list[dict],
    by_strat: dict[str, list[int]],
    keyword_rows: list[tuple[str, float, int]],
) -> list[str]:
    """Heuristic, non-magical suggestions. Conservative — only fires on clear signals."""
    out = []
    n = len(sessions)

    # Unused strategies
    seen = set(by_strat.keys()) if by_strat else set()
    all_strats = {"entertainment", "revival", "strong_sensation", "diversion",
                  "discharge", "mental_work", "solace"}
    if n >= 10:
        missing = all_strats - seen
        if missing:
            out.append(
                f"Strategies never picked: {', '.join(sorted(missing))}. "
                f"Either you don't encounter contexts that call for them, or the "
                f"LLM is under-selecting them. Worth a manual prompt-evaluation pass."
            )

    # Strategies that are reliably bad
    for strat, ratings in by_strat.items():
        if len(ratings) >= 3 and mean(ratings) < -0.5:
            out.append(
                f"`{strat}` is averaging {mean(ratings):+.2f} across {len(ratings)} "
                f"rated sessions — Pulse may be over-picking it, or the trajectories "
                f"it generates aren't landing. Inspect the worst sessions for patterns."
            )

    # Keywords with very low ratings
    bad_keywords = [(w, a, n_) for w, a, n_ in keyword_rows[:5] if a < 0 and n_ >= 2]
    if bad_keywords:
        words = ", ".join(f"`{w}`" for w, _, _ in bad_keywords)
        out.append(
            f"Negative-rating clusters around: {words}. These contexts may need "
            f"different strategy selection rules in the LLM prompt."
        )

    # Low rating coverage
    rated_pct = sum(1 for s in sessions if s.get("post_session_rating") is not None) / n if n else 0
    if n >= 5 and rated_pct < 0.5:
        out.append(
            f"Only {rated_pct * 100:.0f}% of sessions are rated. Rating coverage is "
            f"the single biggest input to v1 — try to rate everything, even with "
            f"just a number."
        )

    return out


def main():
    parser = argparse.ArgumentParser(description="Generate a Pulse session report.")
    parser.add_argument(
        "--sessions-dir",
        default="pulse/data/sessions",
        help="Directory of session JSON files (default: pulse/data/sessions)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Write report to this file instead of stdout",
    )
    parser.add_argument(
        "--since",
        help="Only include sessions from this date forward (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    sessions_dir = Path(args.sessions_dir)
    if not sessions_dir.exists():
        print(f"❌ No sessions directory at {sessions_dir}", file=sys.stderr)
        sys.exit(1)

    since = datetime.fromisoformat(args.since) if args.since else None
    sessions = load_sessions(sessions_dir, since=since)

    if not sessions:
        print("No sessions found.", file=sys.stderr)
        sys.exit(0)

    report = format_report(sessions)

    if args.output:
        Path(args.output).write_text(report)
        print(f"📝 Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
