---
name: venti-discipline
description: Venti's production methodology. Load BEFORE writing or changing any code, docs, config, or deploy process in this repo — it encodes the coding discipline, privacy invariants, spec-as-ledger process, testing gates, and shipping rules every model working on Venti must follow. Also load when planning work, reviewing changes, or deciding whether to build something at all.
---

# The Venti way — discipline, structure, methodology

This skill is the continuity contract between models and sessions. The
codebase was built under a specific mindset; your job is to continue it,
not to reinvent it. When this document and the code disagree, the code
and its tests are ground truth — then fix this document in the same
commit.

## Mindset (read before anything else)

1. **Privacy is the product, not a feature.** Venti's one promise —
   "nothing you write here is stored" — is engineered to be *literally,
   mechanically true* (schemas with no free-text columns, byte-level
   tests, event-shaped logs). Every change is evaluated first against
   this promise. When a feature and the promise conflict, the feature
   loses, every time.
2. **The spec is a ledger, not a plan.** `docs/venti-web-build-spec.md`
   records decisions the way an accountant records transactions:
   T-numbered, dated, with rationale, and amended — never silently
   rewritten. Success criteria were pinned before data existed so
   goalposts cannot move.
3. **Small verified slices, shipped immediately.** One coherent change →
   verify → commit → push. No long-lived local work, no "I'll push when
   it's all done" — uncommitted work is a ghost scaffold and this
   project forbids them.
4. **Scope is defended.** The spec's "What we are NOT building (hold the
   line)" section is a real fence. Ideas that cross it are recorded as
   future conversations, not built.
5. **Honesty in output.** User-facing copy, docs for outsiders, and
   commit messages state what is true, including limitations. (See
   `docs/for-clinical-reviewers.md` for the register: every claim
   code-verifiable, caveats stated plainly.)

## Process for any change

1. **Read first:** `CLAUDE.md` (standing rules), then the relevant spec
   section. Find the T-task your change belongs to. If none exists, the
   change *is* a new T-entry — write it (see Documentation methodology).
2. **Check the fence:** does this cross "What we are NOT building"? If
   yes, stop and surface it to the owner instead of building.
3. **Check the phase:** read "Current phase" at the bottom of this skill.
   During a live beta, production has real testers — prefer additive,
   reversible changes; avoid schema migrations and behavior changes to
   the core loop unless asked.
4. **Implement the smallest slice that can be verified end-to-end.**
5. **Verify** (see Testing & gates) — actually run it, don't reason that
   it probably works.
6. **Document in the same change:** behavior or process changed → spec
   amendment; ops changed → playbook; methodology changed → this skill.
7. **Commit and push immediately** (see Git & shipping).

## Privacy invariants — hard rules, never traded away

- **Vent text lives only in request memory.** It never reaches: a log
  line, a cookie, a server disk, a database, an error message, a Spotify
  artifact (playlist names/descriptions are fixed templates), or an
  analytics event. LLM error messages can quote model output — log
  exception **class names only**, and use `raise ... from None` on
  user-facing error paths.
- **The event store holds metadata only.** `web/app/store.py` has no
  free-text columns and an allowlisted event enum. Nothing text-shaped is
  ever passed to `store.record_event` — no new string parameters beyond
  validated enums. Store writes are best-effort: analytics must never
  break a vent.
- **Logs are event-shaped:** `log.info("<event>", extra={...fields})` —
  named events with typed fields, never request bodies, never IPs, never
  identity (the one exception: `spotify_identity` after OAuth, an owner
  decision for allowlist debugging, T5.6).
- **No identity in analytics.** No accounts, no user IDs, nothing to join
  a row to a person. Per-user dashboards/tracking were explicitly
  rejected; per-person insight comes from the owner's personal
  follow-ups, off-repo.
- **Spotify artifacts are private by default** and never contain
  vent-derived text; playlist labels are validated against the seven
  canonical strategy labels, byte-for-byte.
- **Never open `.env`, `.spotify_cache`, or any file holding live
  tokens** — not even to list key names. Report from metadata only.
- **Crisis screen shows no product mechanics** — resources and warmth
  only; a crisis decline records the event name alone.

Before committing any change that touches a data path, mechanically
check: does any new code path let user text reach `extra=`, a DB column,
an exception message, an HTTP response header, or a Spotify API payload?

## Coding standards (match the existing register)

- **Module docstrings carry the why.** Every module opens with: what it
  is, which T-task shaped it, the invariants it upholds, and any
  platform caveats. A reader should understand the module's constraints
  without reading the spec. Follow the density of `web/app/store.py` or
  `web/app/routers/vent.py`.
- **Comments state constraints the code can't show** — platform
  behavior, ordering requirements, why the obvious alternative is wrong.
  Never narration of what the next line does.
- **Stdlib first.** SQLite over an ORM, `secrets.compare_digest` over a
  library, zero new dependencies as the default. A new dependency needs
  a spec-level justification.
- **Validate at the boundary:** pydantic models with enums
  (`MMRStrategy`), bounded ints (`Field(ge=-2, le=2)`), regex-constrained
  strings (`spotify:track:` URIs), canonical-label validators. Arbitrary
  client strings never flow inward.
- **Fail fast on config:** missing env vars produce one readable startup
  message naming every missing var (`web/app/config.py` pattern).
  Optional-with-fallback vars (e.g. `DATABASE_PATH`) are read from
  `os.environ` at call time, not import time, so tests and deploys can
  repoint them.
- **User-facing error copy is lowercase, warm, and actionable**
  ("connect spotify first — then saving works."). HTTP semantics are
  deliberate: 401 = "your session is no good, re-auth fixes it"; 403 =
  "app-level denial, re-auth won't help". Don't blur them.
- **Frontend: `textContent` only** — never `innerHTML` with data.
- **Best-effort side work** (identity fetch, analytics writes) is
  wrapped so its failure never breaks the primary action, and its
  failure is logged as an event with an error class name.

## Testing & gates

- `pytest` for `web/tests` and `pulse/tests` must pass before any push.
- **Data-path changes extend the privacy tests** — the byte-level
  "vent text never reaches the DB file / log stream" pins are the
  project's crown jewels; new storage or logging surface gets equivalent
  pins in the same commit.
- **LLM prompt/pipeline changes require the evals gate** before deploy:
  ≥14/15 core, 5/5 crisis/near-miss, 1/1 injection (`evals/run_eval.py`,
  API backend). Crisis triage prefers over-caution by design — an eval
  "improvement" that weakens that bias is a regression.
- **Verify user-visible changes by hand** on the deployed app when
  feasible; storage changes get a redeploy-survival check (write → 
  redeploy → confirm the data is still there).
- Rate limits, cookie flags, and log grep were hand-verified for the
  T5.4 gate; changes to those areas re-verify by hand.

## Documentation methodology

- **Spec amendments, never silent edits.** New decisions get the next
  T-number, a date, the decision owner, the rationale, and explicit
  "supersedes X" language when overriding an earlier rule (T5.10
  superseding "no database" is the template). History stays readable as
  history.
- **Success criteria are immutable** once data collection starts.
- Ops/process → `docs/beta-playbook.md`. Outward-facing documents live
  in `docs/` and every claim in them must be verifiable in code.
- `.env.example` documents every env var the app reads, with the
  deployment caveats inline.

## Git & shipping

- Work happens on the `web` branch. **Every commit is pushed
  immediately** — no asking, no batching (owner rule: public-by-choice,
  anti-ghost-scaffold).
- Commit style: `type(scope): imperative summary (T#)` — e.g.
  `fix(spotify): add tracks via /playlists/{id}/items — Feb 2026
  migration, part 2 (T5.7)`. Reference the T-task whenever one applies.
- The repo is public. Nothing sensitive is ever committed; `.env`,
  `.spotify_cache`, `data/`, and `DIAGNOSTIC_REPORT.md` are gitignored
  for cause — never weaken those entries.
- Railway deploys from `web` on push — treat every push as a deploy.

## Platform constraints worth knowing (as of 2026-07)

- **Spotify Feb 2026 policy (T5.7, T5.11):** dev-mode apps get one
  Client ID, max 5 authorized users, owner must keep Premium active;
  track adds go via `POST /playlists/{id}/items`; off-profile visibility
  needs an explicit Change Details `PUT {"public": false}` before tracks
  are added. Extended quota is a post-beta conversation and has gotten
  materially harder.
- **Railway:** container FS is ephemeral — durable data lives on the
  Volume at `/data` (`DATABASE_PATH=/data/venti.db`). Log retention (7
  days Hobby) is shorter than the beta window; the DB is authoritative,
  logs are ops visibility only.

## Current phase — LIVE BETA (started 2026-07-07; update when it ends)

- ~25 real testers over 14 days, two tiers (T5.11): ~21 core testers on
  the auth-free vent/listen/rate loop; 4 save-enabled testers on the
  Spotify allowlist beside the owner.
- **Deploy conservatism applies.** Every push deploys to people mid-beta.
- Metrics: owner exports `/api/admin/export` Mon + Thu and runs
  `python tools/rating_report.py` — don't change event semantics
  mid-window or the scorecard's history breaks.
- Success criteria (pinned): ≥40% return rate (from follow-ups, not
  telemetry), mean rating > +0.5 over ≥30 rated sessions, ≥half say the
  reveal "got them".

## Maintaining this skill

This file is methodology, and methodology changes are spec-worthy: when
a rule here changes, update this file **in the same commit** as the
change that invalidated it, and note it in the spec if it alters process.
A future session should never find this skill describing a project that
no longer exists.
