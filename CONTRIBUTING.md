# Contributing to Venti

Thanks for being here. Venti is small and early — at v0.3 with one primary maintainer — which means contributions have outsize impact. A typo fix is welcome. A new music backend adapter changes the project's reach. There's no "too small to bother."

## What kinds of contributions are most useful

Roughly in priority order:

**Music backend adapters.** The single biggest thing limiting Venti's usefulness is that it only works with Spotify. Adapters for Apple Music, YouTube Music, Tidal, SoundCloud, or even Last.fm scrobbling would each meaningfully expand who can use this. The `pulse/spotify_client.py` module is the pattern to copy — it's intentionally small. If you're thinking about a new adapter, open a Discussion first to talk through the provider interface; that saves you from refactoring twice.

**Eval scenarios.** The current eval pack (`evals/eval_pack.md`) has 15 scenarios across a deliberate range of emotional registers, but real gaps exist — particularly cultural variation beyond a single Hindi scenario, neurodivergent emotional framing, and scenarios where `diversion` or `strong_sensation` are the primary expected strategy. PRs that add a scenario alongside the current output it produces are especially valuable — they document failure modes whether or not the scenario gets fixed in the same PR.

**Prompt improvements.** The strategy selection rules in `pulse/inference.py` are deliberately rule-based and explicit so they're auditable and improvable. If you find a scenario where Venti reliably picks the wrong strategy, a PR adjusting the relevant rule (with the eval result demonstrating the improvement) is the cleanest contribution shape.

**Introspection tool improvements.** `tools/introspect.py` analyzes session history. Easy wins include: better multilingual keyword extraction (currently it drops non-Latin scripts), time-of-day patterns, per-day-of-week analysis, embedding-based clustering of vent texts.

**Documentation.** The README is the front door. If something in it confused you on first read, fixing that is high-leverage work. Same for any other docs that are currently sparse.

## What probably won't be merged right now

Venti is being kept deliberately scoped at v0.x. Some things are out of scope until later versions:

- Mobile app development
- Multi-user backend, hosted version, server-side personalization
- Generative music (Suno-style track creation)
- Therapy or clinical positioning (Venti is not a medical device and won't be one)
- Major architectural rewrites without prior discussion in an issue

If you have a contribution that touches any of these, please open a Discussion first so we can talk through scope before you spend time on a PR.

## Development setup

```bash
git clone https://github.com/<your-fork>/venti-music.git
cd venti-music
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Set the environment variables described in the README. Run the smoke tests to confirm everything's wired up:

```bash
python3 pulse/tests/test_trajectory.py
python3 pulse/tests/test_inference.py
```

Both should report all checks passing.

If your changes could affect inference or strategy selection, also run the full eval pack:

```bash
python3 evals/run_eval.py
```

This takes a few minutes (each scenario triggers an LLM call) and uses your configured Anthropic API key or Claude Code subscription. Compare your results against the baseline in `evals/results/SUMMARY.md`. A regression in any previously-passing scenario should be addressed in the PR.

## Pull request etiquette

Small PRs are easier to review than big ones. Aim for one logical change per PR.

Include in your PR description:

- What problem the PR solves (link an issue if one exists)
- A brief description of the approach
- Eval pack results if your change touches inference, trajectory, or query generation

Don't worry about getting style perfect on the first push — feedback is friendly, not gatekept. The goal is to make this easier to use and easier to contribute to.

## Code of conduct

We follow the [Contributor Covenant](CODE_OF_CONDUCT.md). In short: be the kind of collaborator you'd want to work with. Disagreements about technical direction are fine and welcome. Personal attacks, harassment, or contempt are not.

## Questions?

Open a Discussion. That's the right venue for "is this the right approach?" or "I have an idea but I'm not sure if it fits." Issues are for concrete bugs and well-scoped feature requests; Discussions are for everything else.