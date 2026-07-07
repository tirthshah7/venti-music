# Venti beta playbook — recruiting, running, and measuring the 25-user beta

Operational companion to `docs/venti-web-build-spec.md`. The spec decides
*what counts as success*; this document is the process for getting 25 real
people through 14 days and measuring the three criteria without breaking
the privacy design.

## The two data systems (and the wall between them)

Everything in this beta is measured by exactly two instruments:

1. **Telemetry (aggregate, anonymous)** — the SQLite event store, exported
   via `/api/admin/export` and summarized by `tools/rating_report.py`.
   It knows *what the system did* (sessions, strategies, ratings, saves,
   crisis declines, latency) and by construction cannot know *who did it*
   or *what they wrote*.
2. **Tester sheet (personal, manual, off-repo)** — a private spreadsheet
   you keep in your own Drive/Notes, never committed to this repo. It
   knows *who the testers are* and what they told you directly.

**The wall:** these two are never joined. Don't try to attribute event
rows to individual testers (by timestamp correlation or otherwise) — the
"nothing you write here is stored / no accounts" promise is also the
pitch, especially to the psychologists. Per-user telemetry dashboards are
rejected for this beta; criterion 1 (return rate) and criterion 3 (the
reveal lands) come from conversations, not logs.

## Pre-flight

No invite goes out until the T5.4 beta gate checklist in the build spec is
fully checked (evals, rate limits verified by hand, no vent text in logs,
cookie flags, $50 Anthropic hard cap, allowlist populated).

## Invite in waves, not all at once

Spotify dev mode caps the allowlist at 25. Don't spend all 25 slots on
day 1:

- **Wave 1 (5–8 people):** the contacts most likely to actually engage and
  give direct feedback. Their first sessions will surface onboarding
  friction (unclear copy, allowlist misses, OAuth confusion). Fix those
  first.
- **Wave 2 (rest):** goes out 2–4 days later, once wave 1 has proven the
  path from invite email to first rated session works without hand-holding.

The 14-day window starts per-tester (from their first session), so a
staggered start doesn't shrink anyone's window.

## Per-tester pipeline

Each person moves through these states; the tester sheet tracks the state.

1. **Shortlisted** — on your candidate list.
2. **Invited** — personal email sent (template A; add the B paragraph for
   psychologists). Individual emails, never BCC blasts — these are
   professional contacts, and the ask is personal.
3. **Accepted** — they replied with their Spotify account email.
4. **Allowlisted** — you added that email in the Spotify Developer
   Dashboard (app → Settings → User Management) *before* sending access.
   This is what makes "Save to Spotify" work; skipping it produces a 403
   on their first save and a bad first impression.
5. **Onboarded** — welcome email sent (template C) with the URL and the
   three-line instructions.
6. **Active** — they've confirmed (or mentioned) a first session.
7. **Nudged** — mid-beta nudge (template D) sent around day 4–5 of their
   window if you haven't heard anything.
8. **Followed up** — 15-minute call or written check-in around day 10–12
   (template E to schedule; question script below). This is where
   criteria 1 and 3 get measured.
9. **Closed out** — thank-you note at the end, with the aggregate results
   once the beta concludes. Professionals gave you their time; showing
   them what it added up to is what makes a second favor possible.

## Tester sheet columns

Name · profession/why invited · email · Spotify account email ·
allowlisted (date) · invited (date) · onboarded (date) · first session
(self-reported date) · second session? (Y/N — **this is criterion 1**) ·
follow-up date · "reveal lands"? (Y/N + their words — **criterion 3**) ·
notable feedback · wave.

## Email templates

Placeholders in angle brackets. Keep them short — busy professionals.

### A — initial invite (all testers)

> Subject: Would you beta test something I built? (10 minutes, 2 weeks)
>
> Hi <name>,
>
> I've built Venti — a small web app where you vent about how you're
> feeling for a few sentences, and it builds you a short playlist designed
> to actually move your emotional state, not just match it. It explains
> its reasoning back to you in one line.
>
> Privacy is the core of the design: nothing you write is ever stored —
> no account, no history, and the system's own database physically has no
> column that could hold your words.
>
> I'm running a 25-person, two-week beta and I'd value you specifically
> because <one honest sentence: their profession/perspective>.
>
> The ask: use it at least twice over two weeks (a session is ~2 minutes),
> tap the rating after each session, and give me 15 minutes of your
> impressions near the end.
>
> If you're in, reply with the email address of your Spotify account —
> I need to add it to the beta allowlist so saving playlists works.
>
> Thanks either way,
> <you>

### B — extra paragraph for psychologists (insert before "The ask")

> Given your clinical background, I'd especially value your read on two
> design decisions: the app classifies each vent into one of seven
> mood-regulation strategies (it aims to *move* the emotional state, not
> mirror it), and it triages crisis language — if a vent indicates acute
> crisis, it declines to make a playlist and shows support resources
> instead. Whether those two behaviors are calibrated right is exactly
> the feedback I can't get from metrics. To be clear about scope: Venti
> is an emotional-regulation companion, not therapy and not a clinical
> tool, and I want the framing to communicate that honestly.

### C — welcome / access

> Subject: You're in — Venti beta access
>
> Hi <name>,
>
> You're on the allowlist. Here's everything:
>
> <https://your-domain>
>
> 1. Type what's on your mind (a few sentences is plenty) and hit vent.
> 2. Listen — and tap the rating row ("did the music move you?") after
>    every session, even if you skip everything else. Those ratings are
>    the beta's entire success metric.
> 3. "Save to Spotify" is optional; it creates a private playlist on your
>    account (connect with the Spotify email you gave me).
>
> Use it whenever you actually have something to vent about over the next
> two weeks — real moments beat test runs. There's a soft limit of a few
> sessions per hour.
>
> If anything breaks or feels off, just reply to this email — friction
> reports are as valuable as ratings.

### D — mid-beta nudge (day 4–5 of silence)

> Subject: How's Venti treating you?
>
> Hi <name> — no pressure, just checking the app hasn't put anything in
> your way. If you've used it: anything feel off? If you haven't had a
> moment worth venting about yet, that's fine too — it works best on real
> ones. One thing that helps me enormously either way: tap the rating
> after any session you do have.

### E — follow-up scheduling (day 10–12)

> Subject: 15 minutes on Venti this week?
>
> Hi <name> — as the beta wraps up, could I get 15 minutes for your
> impressions (call or written, whichever is easier)? Your read is the
> half of the data the metrics can't give me.

## Follow-up question script

Ask in this order; the first two map directly to success criteria.

1. "How many times did you end up using it?" → **criterion 1** (≥2 = returned).
2. "When it showed you the one-line reasoning about why it picked that
   music — did that land? Did it feel accurate to where you were?" →
   **criterion 3**; write their words down verbatim in the sheet. Count it
   only if they affirm it in substance ("it got me"), not politeness.
3. "Did any playlist actually move your state, or just match it?"
4. "Was anything confusing or in your way?" (onboarding friction)
5. For psychologists: "Did the strategy it chose ever feel wrong or
   counterproductive for the state you described?" and "Any concerns about
   the crisis handling or the framing?"
6. "Would you use it again after the beta / who else should try it?"

## Metrics operations

**Cadence: export + scorecard every Monday and Thursday**, and once more
on the final day:

```
curl -H "X-Admin-Token: $TOKEN" https://<domain>/api/admin/export > exports/events-<date>.jsonl
python tools/rating_report.py exports/events-<date>.jsonl
```

Keep the exports and pasted scorecards in a local beta journal (off-repo,
same place as the tester sheet). The DB on the Railway volume is
authoritative, but a twice-weekly local export is the backup against
volume/service loss.

The scorecard *is* the ops dashboard for a 25-person beta: sessions, mean
latency, save rate, crisis declines, rating count/mean/distribution,
per-strategy means, and the criterion-2 gate line. No web dashboard gets
built for this — revisit only after the beta, if the criteria hold and
someone other than the owner needs to read the numbers.

**Where each success criterion comes from:**

| Criterion | Instrument |
|---|---|
| 1. Return rate ≥40% return for a 2nd session | Tester sheet (follow-up Q1) |
| 2. Mean rating > +0.5 across ≥30 rated sessions | Scorecard (`rating_report.py`) |
| 3. ≥half say the reveal "got them" | Tester sheet (follow-up Q2, verbatim quotes) |

30 rated sessions across ~25 testers means the "rate every session"
line in the welcome email is load-bearing — repeat it in the nudge.

## Sharing results with the psychologists

At close-out, send the aggregate picture — never anything per-person
(nothing per-person exists in the telemetry, and the sheet is private):

- Sessions, save rate, and the rating distribution + per-strategy means
  straight from the scorecard.
- Crisis-declined count, with a description of exactly what a triaged
  user sees.
- The privacy architecture, stated as a result in itself: no vent text at
  rest anywhere, schema with no free-text columns, pinned by tests.
- 2–3 anonymized themes from the follow-ups (never attributed quotes
  without explicit permission).

For the clinically-minded, that framing — data minimization, crisis
triage behavior, strategy-level efficacy — is the difference between
"an app that mines feelings" and "a tool designed responsibly"; it's
also the groundwork if you ever want their endorsement or advice on a
more formal evaluation later.
