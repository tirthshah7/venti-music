# Venti

_The repo is `venti-music`. The brand is Venti. The CLI is `vent`._

> A CLI that picks music based on what you vent about, grounded in 70 years of music therapy research.

Venti is a small command-line tool. You type one line describing how you feel — _"third hour on this docker bug and i can't even tell what's broken anymore"_ — and Venti picks a 4-song Spotify playlist designed to actually shift your mood, using the iso principle from clinical music therapy and Saarikallio's seven-strategy framework for music in mood regulation.

It's not "play happy songs when sad." It's closer to what a music therapist would do: meet the listener where they are emotionally, then walk them gradually toward a different state. That difference matters, and the research shows why.

**Status:** v0.3, evaluated against 15 designed scenarios (14 PASS / 1 PARTIAL / 0 FAIL). Genuinely useful, genuinely rough. Built in the open. Contributions welcome.

---

## What problem does this solve

When you're stuck on something hard — debugging, writing, designing, anything that demands sustained focus — your options for managing frustration through music are bad. Spotify's mood playlists are static. Apple Music's stations are generic. Asking an AI DJ for "focus music" gets you the same lo-fi loop everyone else gets. None of these tools know what you're actually working on, why it's wearing you down, or what kind of intervention would actually help.

Venti uses an LLM to read what you wrote, infer your emotional state in two dimensions (valence and arousal — how positive/negative, how intense/calm), and pick one of seven distinct mood-regulation strategies the music psychology literature has identified:

- **Discharge** — let the frustration out cathartically (intense music for anger)
- **Solace** — feel understood, not alone (for sadness, grief, isolation)
- **Revival** — gentle lift to restore energy after depletion
- **Diversion** — orthogonal escape, break the rumination loop
- **Mental work** — contemplative music for processing and reappraisal
- **Entertainment** — sustain an existing positive mood
- **Strong sensation** — peak emotional intensity, for when you want to feel something

The chosen strategy determines the *shape* of the trajectory through music — discharge amplifies before easing, solace stays close to current state without forcing positivity, diversion jumps to unrelated emotional territory. The trajectory is then translated into Spotify searches and played on your active device.

Most music systems pick songs. Venti picks _arcs_.

## The research it's built on

Three foundational ideas, all published:

- **Russell, J. A. (1980).** _A circumplex model of affect._ — Emotions modeled as 2D coordinates (valence × arousal), not discrete labels. "Frustration" and "sadness" are both negative valence but very different arousal, and they call for very different music.
- **Saarikallio, S. (2008).** _Music in Mood Regulation: Initial Scale Development._ Musicae Scientiae. — Identified the seven distinct strategies above through empirical work on how people actually use music to regulate mood.
- **Starcke, K. & von Georgi, R. (2024).** _Music listening according to the iso principle modulates affective state._ Psychology of Music. — Meeting the listener where they are first, then shifting, beats jumping straight to the target mood. Clinical music therapy has used this for 75+ years; the 2024 paper validates it for everyday self-regulation.

Venti operationalizes these three into a working pipeline. None of them are individually novel — the combination, and the personalization over time from your own session ratings, is the moat.

## How it actually works

```
your vent text  ──►  Claude (emotion inference)  ──►  (valence, arousal, strategy)
                                                              │
                                                              ▼
                                                    trajectory generator
                                                    (shape depends on strategy)
                                                              │
                                                              ▼
                                                    Claude (search queries)
                                                              │
                                                              ▼
                                                    Spotify search + playback
                                                              │
                                                              ▼
                                                    session saved locally
                                                    (ratings become training data
                                                     for the next version)
```

The CLI is intentionally small. Seven Python files do the real work. No backend, no accounts, no telemetry. Sessions are JSON files in your local `data/` folder. You own them.

## A real example

Input:

```bash
$ vent "stuck on this docker bug for two hours and nothing is working"
```

What Venti does:

```
🧠 Inferring emotional state...
   Current state: valence=-0.70, arousal=+0.75
   Target state:  valence=-0.30, arousal=+0.50
   Strategy: discharge
   Reasoning: Two hours stuck on a Docker bug signals mounting coding
   frustration — negative valence with high arousal from repeated failed
   attempts. Discharge lets the frustration vent cathartically through
   intense music before gradually easing toward calmer focus.

🛤️  Generating trajectory...
   Waypoint 1: valence=-0.80, arousal=+0.85    (amplify the catharsis)
   Waypoint 2: valence=-0.70, arousal=+0.68
   Waypoint 3: valence=-0.50, arousal=+0.62
   Waypoint 4: valence=-0.30, arousal=+0.50    (target reached)

🔍 Generating search queries...
   Query 1: "angry punk catharsis"
   Query 2: "intense rock frustration"
   Query 3: "hard alternative release"
   Query 4: "driving indie resolve"

🎵 Searching Spotify...
📋 Playlist:
   1. Catharsis — AlicebanD
   2. ...
   3. ...
   4. ...

▶️  Playing.
```

Notice what the system did *not* do: pick "happy" or "motivational" music. Pushing someone frustrated toward upbeat music tends to backfire — the brain rejects it as dismissive of the real feeling. Discharge honors the frustration first, then shifts.

---

## Setup

Venti is a CLI written in Python. You'll need three things to run it:

1. **Python 3.10+**
2. **Spotify Premium** (the API can only control playback on Premium)
3. **Either an Anthropic API key (recommended) OR Claude Code installed locally**

### 1. Clone and install

```bash
git clone https://github.com/<your-github>/venti-music.git
cd venti-music
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Get a Spotify developer app (one-time, ~5 minutes)

Venti needs a Spotify Client ID and Secret to access the API. Because of Spotify's developer-mode restrictions, **you need to create your own developer app** rather than using a shared one. This is normal for open-source Spotify tools.

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and sign in with your Spotify account.
2. Click "Create app."
3. Fill in any name and description.
4. Set the redirect URI to **exactly** `http://127.0.0.1:8888/callback` (Spotify rejects `localhost` over HTTP since 2025).
5. Check "Web API" under "Which API/SDKs."
6. Save. Then click "Settings" on your new app's page — copy the Client ID, click "View client secret" and copy that too.

### 3. Choose your LLM access method

**Option A: Anthropic API (recommended, costs ~$0.02 per vent session)**

Get a key at [console.anthropic.com](https://console.anthropic.com). New accounts get $5 of free credit, which is enough for ~250 vent sessions.

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

**Option B: Claude Code subprocess (free if you have a Claude Max plan)**

If you have an active Claude Max subscription, Venti can route inference through `claude -p` instead of the API. No additional billing. Install Claude Code from [docs.claude.com/claude-code](https://docs.claude.com/claude-code) and run `claude login`. Venti will auto-detect and use it if no API key is set.

### 4. Set your Spotify credentials

```bash
export SPOTIFY_CLIENT_ID="paste-your-client-id"
export SPOTIFY_CLIENT_SECRET="paste-your-client-secret"
export SPOTIFY_REDIRECT_URI="http://127.0.0.1:8888/callback"
```

(Add these to your `.zshrc` or `.bashrc` if you don't want to set them every session.)

### 5. Run it

Make sure Spotify is open and playing (or paused) on some device — a phone, the desktop app, the web player, any device. The API can redirect playback to an active device but can't wake a sleeping one.

```bash
vent "stuck on this docker bug for two hours and nothing is working"
```

First run will open your browser for Spotify OAuth. Approve, copy the redirect URL back into the terminal, and it'll start playing.

After listening, rate the session:

```bash
vent rate 1 "the punk worked, third track was a perfect bridge"
vent rate -1 "too aggressive, skipped most of them"
```

(Ratings are -2 to +2: how much did the playlist actually shift your mood? Notes are optional but help when you look back at your session history.)

---

## Project status

This is **v0.3** — the first public release. It's small (~900 lines of real code), tested, and evaluated, but explicitly experimental.

### What works

- Emotion inference from natural-language vent text, including non-English (tested with Hindi, expected to work in any language Claude handles)
- All seven MMR strategy types implemented with distinct trajectory shapes
- Spotify search + playback integration
- Local session storage with optional ratings + notes
- Introspection tool to analyze your own session history (`python tools/introspect.py`)
- Evaluation framework with 15 designed scenarios (`evals/eval_pack.md`)

### What's known to be rough

- **Spotify is the only music backend.** Apple Music, YouTube Music, etc. would need new adapters. Excellent first-contribution opportunity.
- **The entertainment trajectory has a known bug** when current and target emotional states differ significantly — it oscillates near current state instead of moving toward the target. Will be filed as a tracked issue once the repo is published.
- **No personalization yet.** Sessions are saved but the inference doesn't learn from your ratings. That's v1.
- **No auto-detection trigger.** You have to manually run `vent`. v1 will add scanning of existing chat/journal channels for frustration markers.
- **One user at a time.** Each user needs their own Spotify developer app due to Spotify's quota policies.

### What was deliberately not built

- No mobile app (yet — possibly v2)
- No web UI (CLI only; v1 might add a small TUI)
- No multi-user backend (Venti is local-first by design for v0)
- No telemetry (nothing leaves your machine except API calls you make yourself)

---

## Evaluation

Venti includes an evaluation pack of 15 scenarios spanning a deliberate range of emotional registers — acute grief, sustained work frustration, performance anxiety, social rejection, caregiver burnout, mixed-valence states like pre-wedding nerves, and one Hindi-language scenario.

Current v0.3 result: **14 PASS / 1 PARTIAL / 0 FAIL.**

The methodology, full scenario list, and per-scenario verdicts live in [`evals/`](evals/). Contributors are encouraged to add scenarios that represent emotional registers the current set under-represents — particularly cultural variation, neurodivergent framing, and the diversion / strong_sensation strategies which the current set doesn't test as primary expected outcomes.

To run the eval yourself:

```bash
python3 evals/run_eval.py
```

---

## Contributing

Venti is built in the open and contributions are welcome at any size — typos, documentation, new music backends, prompt improvements, eval scenarios, code refactors, ideas in Discussions.

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup. Good first issues are tagged on the [issues page](../../issues).

The two highest-leverage contribution areas right now:

- **Music backend adapters.** Apple Music, YouTube Music, Tidal, even Last.fm scrobbling. The provider interface in `pulse/spotify_client.py` is small and easy to follow.
- **Eval scenarios.** Add new emotional registers you think Venti handles poorly. PRs that include a new scenario plus the current Venti output are especially welcome — they document failure modes whether or not the scenario gets fixed.

Areas explicitly NOT prioritized for v0.x:

- Mobile UI
- Multi-user backend
- Generative music (Suno-style)
- Therapy/clinical positioning (Venti is not a medical device)

---

## License

MIT. See [LICENSE](LICENSE).

In plain English: do whatever you want with this code, including commercially. Just keep the copyright notice. No warranty.

---

## A note from the maintainer

This project exists because I was venting about a debug session in one chat window while bad music played in another, and I noticed the two could talk to each other. The first working version took a weekend. The version you see here took a few more weeks of careful iteration, mostly on the psychology framing and the evaluation methodology.

I think there's something real here, but I'm sharing it early — before personalization, before mobile, before any commercial work — because the core hypothesis (LLM-routed mood regulation grounded in actual research) is more interesting if other people get to push back on it, find what breaks, and shape what comes next.

If you build something with this, fork it, port it to a music service I haven't covered, or find a context where it fails badly, I'd genuinely like to hear about it. Issues and Discussions are both watched.
