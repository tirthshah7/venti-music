"""
Pulse CLI — the `vent` command.

Pipeline:
    vent text → infer emotion → trajectory → search queries → Spotify tracks → play
"""
import os
import sys
import argparse
from datetime import datetime

from .models import VentSession
from .inference import EmotionInference
from .trajectory import generate_trajectory
from .query_generator import QueryGenerator
from .spotify_client import SpotifyClient
from .storage import SessionStore


def cmd_vent(args):
    store = SessionStore()

    print(f"\n💭 Vent: {args.text}")
    if args.context:
        print(f"📋 Context: {args.context}")

    print("\n🧠 Inferring emotional state...")
    inference = EmotionInference()
    result = inference.infer(args.text, context=args.context or "")

    current = result["current_emotion"]
    target = result["target_emotion"]
    strategy = result["strategy"]
    reasoning = result["reasoning"]

    print(f"   Current state: valence={current.valence:+.2f}, arousal={current.arousal:+.2f}")
    print(f"   Target state:  valence={target.valence:+.2f}, arousal={target.arousal:+.2f}")
    print(f"   Strategy: {strategy.value}")
    print(f"   Reasoning: {reasoning}")

    print("\n🛤️  Generating trajectory...")
    trajectory = generate_trajectory(current, target, strategy, n_waypoints=4)
    for i, wp in enumerate(trajectory):
        print(f"   Waypoint {i+1}: valence={wp.valence:+.2f}, arousal={wp.arousal:+.2f}")

    print("\n🔍 Generating search queries...")
    query_gen = QueryGenerator()
    queries = query_gen.generate_queries(trajectory, strategy)
    for i, q in enumerate(queries):
        print(f"   Query {i+1}: \"{q}\"")

    print("\n🎵 Searching Spotify...")
    spotify = SpotifyClient()
    tracks = spotify.build_playlist_from_queries(queries)

    if not tracks:
        print("   ⚠️  Could not find any tracks. Check Spotify connection.")
        return

    print(f"\n📋 Playlist:")
    for i, track in enumerate(tracks):
        artists = ", ".join(a["name"] for a in track["artists"])
        print(f"   {i+1}. {track['name']} — {artists}")

    if not args.dry_run:
        print("\n▶️  Starting playback...")
        try:
            spotify.play_tracks([t["uri"] for t in tracks])
            print("   Playing.")
        except Exception as e:
            print(f"   ⚠️  Playback failed: {e}")
            print("   Open Spotify on a device and try again, or use --dry-run.")

    session = VentSession(
        timestamp=datetime.now().isoformat(),
        trigger_type="manual",
        vent_text=args.text,
        context=args.context or "",
        current_emotion=current,
        target_emotion=target,
        strategy=strategy,
        reasoning=reasoning,
        trajectory=trajectory,
        track_ids=[t["id"] for t in tracks],
    )
    path = store.save(session)
    print(f"\n💾 Session saved: {path}")
    print("   Run `vent rate <-2..+2> [\"note\"]` after listening to log how it felt.")


def cmd_rate(args):
    store = SessionStore()
    session = store.latest()
    if not session:
        print("No sessions found.")
        return
    session.post_session_rating = args.rating
    if args.note:
        session.notes = args.note
    store.save(session)
    print(f"✅ Rated last session: {args.rating:+d}" + (f" — {args.note}" if args.note else ""))


def cmd_history(args):
    store = SessionStore()
    sessions = store.all_sessions()[-args.n:]
    if not sessions:
        print("No sessions yet.")
        return
    for s in sessions:
        rating = f" [{s.post_session_rating:+d}]" if s.post_session_rating is not None else " [-]"
        print(f"{s.timestamp[:16]}  {s.strategy.value:18s}{rating}  \"{s.vent_text[:60]}\"")


def main():
    parser = argparse.ArgumentParser(prog="vent", description="Pulse — emotion-aware music")
    sub = parser.add_subparsers(dest="cmd")

    p_vent = sub.add_parser("vent", help="Vent and start a session (default)")
    p_vent.add_argument("text", help="What you're feeling / why")
    p_vent.add_argument("--context", "-c", help="What you're working on")
    p_vent.add_argument("--dry-run", action="store_true", help="Don't actually play, just plan")

    p_rate = sub.add_parser("rate", help="Rate the most recent session")
    p_rate.add_argument("rating", type=int, choices=[-2, -1, 0, 1, 2])
    p_rate.add_argument("note", nargs="?", default=None)

    p_hist = sub.add_parser("history", help="List recent sessions")
    p_hist.add_argument("-n", type=int, default=10)

    argv = sys.argv[1:]
    if argv and argv[0] not in {"vent", "rate", "history", "-h", "--help"}:
        argv = ["vent"] + argv

    args = parser.parse_args(argv)

    if args.cmd == "vent":
        cmd_vent(args)
    elif args.cmd == "rate":
        cmd_rate(args)
    elif args.cmd == "history":
        cmd_history(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
