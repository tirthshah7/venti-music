# Venti — pathway ledger for what comes after the beta

**Status: options, not commitments.** The build spec's "What we are NOT
building (hold the line)" fence stands untouched until the beta concludes
and the data is read. This document drafts the Phase-6+ conversations in
advance so momentum survives the pause: what *could* be built, how, in
what order, and what each path costs. Nothing here gets built without a
T-numbered spec amendment first — that's the graduation ceremony for any
item on this list.

**How to read an entry:** each pathway states *what*, *why*, its *gate*
(what must be true before it starts), a *how* sketch, its *privacy
implications* (the non-negotiable lens), and an *effort class* (S/M/L —
days / weeks / a month-plus of focused work).

**The one rule that survives every pathway:** vent text is never stored —
not with accounts, not with personalization, not on mobile, not ever.
Every pathway below was designed under that constraint; if a future idea
can't work under it, the idea changes, not the constraint.

---

## 0. First: let the beta data choose the direction

The three criteria don't just pass/fail the beta — each failure mode
points at a different pathway to prioritize:

| Outcome | What it means | Pathway to prioritize |
|---|---|---|
| Criterion 2 fails overall (mean ≤ +0.5) | The playlists don't move people | §6 Efficacy before anything else |
| Criterion 2 fails for specific strategies | Some trajectories are miscalibrated | §6 per-strategy work; psychologist input |
| Criterion 1 fails (< 40% return) | One-shot novelty, no habit | §2 PWA + gentle return mechanics; §4 personalization |
| Criterion 3 fails (reveal doesn't land) | The reasoning line reads generic | §6 reveal/prompt work |
| All three pass | The core loop works | §3 accounts → §4 personalization → §1/§2 reach |

Run `tools/rating_report.py` per-strategy numbers and the follow-up notes
side by side before picking anything from this document.

---

## 1. Web app evolution (near-term, low-risk)

**What:** polish the existing single-page app without changing its
nature: streaming reveal, better mobile ergonomics, shareability of the
*concept* (never the content).

**Why:** cheapest wins available; most improve the beta's own metrics if
shipped between waves.

**Gate:** none for non-core-loop polish; core-loop changes wait for the
beta window to close (deploy conservatism).

**How:**
- **Streaming reveal (also a latency win, see §5):** show strategy +
  reasoning the moment inference returns, then fill tracks as Spotify
  search completes. The wait feels half as long without making anything
  faster.
- **Progressive Web App (PWA):** manifest + service worker + install
  prompt. Venti becomes "an app on the home screen" with zero app-store
  involvement. This is deliberately the first "mobile app" step (§2).
- **Session-less continuity:** "vent again" flow already exists; a
  client-side-only "how this session compared to your last" (localStorage,
  never server-side) is possible without touching the privacy model.

**Privacy:** no change; localStorage experiments must be additive and
clearly "your device remembers this, we don't."

**Effort:** S per item.

## 2. Mobile app

**What:** Venti on phones — where venting actually happens.

**Why:** the natural venting moment is mobile; a laptop-only tool misses
most of them.

**Gate:** beta passes; PWA (§1) shipped first and its install/return
numbers read.

**How — staged, cheapest reach first:**
1. **PWA (weeks, not months):** installable, offline shell, full-screen.
   Spotify embeds work in mobile browsers. This probably captures 80% of
   the value.
2. **Native wrapper (Capacitor or similar)** only if the PWA hits real
   limits (deeper Spotify hand-off, better audio session behavior, app
   store presence as distribution).
3. **True native** is a business decision, not a technical one — only
   with real user volume and revenue (§8).

**Watch out for:**
- App-store review of mental-health-adjacent apps: keep the non-clinical
  framing airtight (the `for-clinical-reviewers.md` register); no
  medical claims anywhere in store copy.
- Push notifications for return habit ("a gentle check-in") require a
  device token — that's an identifier. Design as strictly opt-in,
  device-scoped, and content-free ("venti is here" — never referencing
  any prior session). Ties into §3.
- Spotify playback on mobile: embeds are fine; the full Spotify iOS/
  Android SDK requires the user's Spotify app + auth, which reopens the
  allowlist constraint (§7).

**Privacy:** push tokens are the first identifier-shaped thing in the
system; they live in their own table, joined to nothing.

**Effort:** PWA = S/M; wrapper = M; native = L.

## 3. User management (accounts — as an opt-in tier, never a wall)

**What:** optional accounts. The anonymous loop remains fully functional
and un-paywalled, forever — that's the promise that makes the product
trustworthy, and it stays literally true for everyone who doesn't opt in.

**Why:** three things need identity to exist at all: cross-device
continuity, personalization (§4), and any paid tier (§8). Nothing else
does.

**Gate:** beta passes; a spec amendment defines exactly what an account
stores before any code.

**How:**
- **Auth:** Spotify OAuth already exists in the codebase as an identity
  source — save-enabled users are "account-shaped" already. Add email
  magic-links only if non-Spotify users need accounts.
- **What an account stores (complete list, enforced by schema like the
  event store):** account id, created-at, auth linkage, notification
  opt-in, and the personalization record from §4 — which is strategy/
  rating metadata only. **No vent text column exists, same byte-level
  test discipline as T5.10.**
- **What it never stores:** vent text, inferred emotional states tied to
  timestamps beyond what the anonymous store already keeps, contact
  graphs, anything sellable.
- **Data rights from day one:** self-serve export (JSON) and delete
  (hard delete, cascade). Cheap to build at schema time, expensive to
  retrofit — and psychologist-reviewer credibility depends on it.
- **Rate limiting** moves from IP to account for logged-in users —
  fixes shared-IP false positives.
- Session cookie infrastructure (signed, allowlisted keys) already
  exists and extends naturally.

**Privacy:** the frontend promise gets one honest amendment for account
holders: "nothing you write is stored — with an account, we remember
which strategies work for you (never your words)."

**Effort:** M.

## 4. "Personal-level model" — personalization without betraying the promise

**What:** Venti gets better at choosing strategies *for you* the more
you rate.

**Why:** the single highest-leverage product idea available. The seven
strategies genuinely differ per person (Saarikallio's own finding);
today every user gets population-default behavior.

**The key architectural insight:** everything worth learning about a
user is **metadata the system already emits** — (strategy, rating)
pairs. Personalization needs zero vent text, zero content analysis,
zero conversation history. It is a preferences problem, not a language
problem.

**Gate:** accounts (§3) exist; ≥ some minimum rated sessions per user
(cold-start threshold, e.g. 5).

**How — three stages, in order:**
1. **Per-user strategy priors (the real win, and it's small):** for each
   account, maintain rating stats per strategy — effectively a contextual
   bandit over 7 arms. At vent time, the LLM proposes its top strategies
   from context (as now); the user's priors break ties and veto
   consistently-negative strategies. Thompson sampling or even simple
   smoothed means over the user's last N ratings is enough at 7 arms.
   The LLM stays in charge of *context* (crisis triage and situational
   fit are never overridden); the prior only tilts.
2. **Prompt-injected preference context:** one structured line in the
   inference prompt — "this user has historically rated discharge +1.4
   (n=9) and solace −0.8 (n=4)" — lets the model integrate priors with
   context judgment instead of a mechanical tie-break. Metadata in,
   never text back.
3. **Track-level preference (later):** per-user artist/genre affinities
   from saved playlists (they're on the user's own Spotify account —
   readable with their existing consent) to bias track search. Stays
   entirely within Spotify-side data the user can see.

**What we deliberately do NOT do:** per-user fine-tuning or training on
vent text. It's a privacy breach, a cost sink, and — the decisive
argument — *unnecessary*: stage 1–2 capture the personalization value at
7-arms scale. Write this refusal into the spec amendment so it's a
recorded decision, not an accident.

**Privacy:** the personalization record is rating metadata under the
same no-free-text schema discipline; exportable and deletable per §3.

**Effort:** stage 1 = S/M; stage 2 = S; stage 3 = M.

## 5. Performance — system latency and cost

**What:** vent-to-reveal is ~8s today (measured: 7.8s in the first live
event row). Target: perceived ≤3s, actual ≤5s.

**Why:** the vent moment is emotionally hot; every second of spinner
cools it.

**Gate:** none — but every inference change passes the evals gate
(≥14/15 core, 5/5 crisis, 1/1 injection) before deploy, no exceptions.
A latency win that weakens crisis triage is a regression, full stop.

**How, in expected-value order:**
1. **Streaming reveal (§1):** biggest *perceived* win, zero model risk.
2. **Parallelize inference and search:** track search currently waits
   for full inference; stream strategy/queries out and start Spotify
   search for early queries while the model finishes.
3. **Model tier experiment:** run the eval pack against smaller/faster
   tiers (e.g. Haiku-class) for the inference step. Decision rule is
   mechanical: fastest tier that still clears the eval gate wins. The
   `latency_ms` column gives before/after evidence for free.
4. **Prompt caching:** the system prompt (strategy rules + crisis
   triage) is static and cacheable; only the vent varies per call.
5. **Query→track cache:** cache Spotify search results per generated
   query string (metadata only) with a short TTL — repeat moods reuse
   catalog work.
6. **Keep-warm:** Railway cold starts add tail latency; a shallow
   health-check ping during active hours is the cheap fix.

**Measurement:** p50/p95 from the event store's `latency_ms`, tracked in
the scorecard — add percentiles to `rating_report.py` when this work
starts.

**Effort:** items 1–2 = S; 3–4 = S each (eval-gated); 5–6 = S.

## 6. Performance — product efficacy (making the music actually move people)

**What:** raising the rating mean, per strategy.

**Why:** if criterion 2 wobbles, this is the whole ballgame; even if it
passes, per-strategy variance will be wide.

**How:**
- **Per-strategy autopsy** of beta ratings (already in the scorecard) +
  follow-up quotes: which strategies underperform, and is it selection
  (wrong strategy for the state) or execution (right strategy, wrong
  tracks)?
- **Selection fixes** live in the inference prompt and grow the eval
  pack: every miscalibration found in the beta becomes a new eval case
  first, then a prompt change that passes it.
- **Execution fixes** live in query generation and trajectory shaping:
  per-strategy curated seed/anchor pools, tighter trajectory waypoints,
  audio-feature filtering if the API tier allows it.
- **The psychologist channel:** standing advisory input on strategy
  calibration and crisis triage — the beta's expert reviewers (see
  `for-clinical-reviewers.md`) are the seed of that channel.
- **Rating granularity:** consider an optional second question ("did it
  match where you were / move you somewhere better?") — one tap, still
  metadata, separates selection failures from execution failures in the
  data itself.

**Effort:** ongoing; each loop = S.

## 7. Platform and catalog independence

**What:** reduce the single-point dependency on Spotify's developer
program, which has tightened twice in 12 months (T5.7, T5.11).

**Why:** 5 allowlist slots is not a growth path; extended quota now
requires a registered business and is materially harder to get.

**How, parallel tracks:**
- **Extended quota application** once there's a legal entity (§8) and
  beta evidence. Prepare the compliance story: private-by-default
  artifacts, no content scraping, the privacy architecture as exhibit A.
- **SoundCloud demo mode** (already filed as a future issue): in-browser
  streams for the no-auth loop — removes Spotify from the *listening*
  path entirely; Spotify remains the *saving* path.
- **Preview-clip fallback:** 30-second previews for reveal-screen
  listening keep the core experience alive under any API weather.
- **Apple Music / MusicKit** only with real user pull; it's a second
  platform relationship to maintain, not a hedge to hold cheaply.

**Privacy:** unchanged; catalog adapters never receive vent text, only
generated queries (same rule as Spotify today).

**Effort:** SoundCloud/preview = M; extended quota = paperwork + time;
Apple = L.

## 8. Scale, infra, and money (kept honest and last)

**Infra gates, in order of when they'll actually matter:**
- SQLite → Postgres only when concurrent writes actually contend or
  accounts (§3) need relational integrity — not before; the T5.10
  store's schema discipline ports as-is.
- Anthropic spend cap raises with traffic; the $50 hard limit stays
  until money exists.
- One Railway service is fine well past the beta; split services are a
  symptom of success, not a preparation for it.

**Monetization (only if all three criteria hold, per the spec):**
- The anonymous core loop is never paywalled — it's the trust anchor
  and the funnel.
- The natural paid tier is the *personal* tier: §3 + §4 (cross-device
  continuity, "venti knows what works for you"), possibly §2 native
  niceties. Price the memory, never the mercy.
- A legal entity is a prerequisite for extended quota (§7) anyway, so
  incorporation is a platform decision as much as a business one.

**Effort:** deferred by design.

---

## Sequencing sketch (assuming the beta passes)

**Phase 6 candidates (first 4–6 weeks after reading the data):**
efficacy autopsy (§6) → streaming reveal + latency items 1–2 (§5/§1) →
PWA (§2 stage 1) → accounts spec amendment written (§3).

**Phase 7:** accounts shipped (§3) → personalization stage 1–2 (§4) →
model-tier + caching experiments (§5 items 3–5).

**Phase 8:** platform independence (§7) + monetization/entity (§8) +
mobile beyond PWA (§2), ordered by what the world looks like then.

Each phase graduates items from this ledger into the spec with T-numbers
and dates, per the `venti-discipline` methodology. Items that stop
making sense get struck through here with a dated one-line reason —
this document keeps its history the same way the spec does.
