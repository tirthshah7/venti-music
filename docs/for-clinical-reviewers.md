# Venti — an overview for clinical reviewers

*Prepared for the psychologists reviewing Venti's beta (July 2026).
Everything below is verifiable against the open codebase; nothing is
aspirational copy.*

## What Venti is

Venti is a small web application for emotional regulation through music.
A person types a short, free-form vent about how they're feeling (a few
sentences; two minutes end to end). The system infers their emotional
state, selects a mood-regulation strategy, and returns a four-track
playlist designed to **move** that state rather than simply mirror it —
along with a single sentence explaining why it chose what it chose.

Venti is **not therapy, not a diagnostic tool, and not a crisis
service**, and it does not present itself as any of those. It is an
emotional-regulation companion in the same category as journaling or a
walk — with one safety behavior described below.

## Theoretical grounding

- **Strategy selection** uses the seven strategies of musical mood
  regulation from **Saarikallio (2008)**: *entertainment* (sustain an
  existing positive mood), *revival* (relax, restore energy), *strong
  sensation* (seek intense emotional experience), *diversion* (orthogonal
  escape from the negative), *discharge* (release negative emotion
  cathartically), *mental work* (contemplate, process, reappraise), and
  *solace* (comfort; feeling understood and not alone).
- **Emotional state** is represented as a point in **valence–arousal
  space** (circumplex model). Each strategy implies a different
  *trajectory* through that space — the playlist is sequenced as a path
  that starts near the person's inferred current state and moves toward
  the strategy's target, in the spirit of the iso principle, rather than
  four songs that all match the starting mood.
- Inference (state, strategy, track queries) is performed by a large
  language model; tracks come from Spotify's catalog.

## What one session looks like

1. The person types a vent (up to 1,000 characters). No account, no
   login, nothing to install.
2. A few seconds later, the reveal: the strategy chosen (e.g. "Discharge"),
   a one-line reasoning statement, the emotional trajectory, and four
   tracks playable in embedded Spotify players.
3. Below the tracks: a single rating — "did the music move you?" on a
   five-point scale (−2 to +2). This rating is the beta's primary
   quantitative signal.
4. Optionally, they can save the playlist (privately) to their own
   Spotify account. During the beta, Spotify's platform rules limit this
   to a handful of testers; listening and rating work for everyone.

## Crisis handling

A triage rule sits **above** all strategy logic: if a vent indicates
crisis-level content — self-harm or suicidal ideation, harm to others,
or acute abuse — the system does not build a playlist. Instead the person
sees a quiet screen with no product mechanics, reading:

> **"that sounds genuinely heavy — and it deserves more than a playlist."**
>
> a real person would be better at this than music. if you're in the US
> or Canada, the **988 Suicide & Crisis Lifeline** is there right now —
> call or text 988, any hour. in Canada you can also call 1-833-456-4566.
> somewhere else? findahelpline.com lists free, confidential helplines
> for nearly every country.
>
> nothing you wrote was stored. venti will be here after — whenever that is.

Design decisions worth your scrutiny:

- The triage is instructed to **prefer over-caution**: when genuinely
  unsure whether the line is crossed, it declines and shows resources.
- Everyday venting (anger, sadness, stress, exhaustion) is explicitly
  *not* treated as crisis — the product exists precisely for those states.
- The triage is a safety net, not a clinical screener, and we make no
  claim that it catches everything.
- Crisis declines are counted (an anonymous counter increments), but what
  was written is never stored — the same privacy rule as everywhere else.

## Privacy and data — precisely what is and isn't collected

This is the part of the design we most want a clinical eye to appreciate
and challenge. The interface promises *"nothing you write here is
stored"*, and that is engineered to be literally true, not a policy
choice that could quietly change:

- **Never stored, anywhere:** the vent text itself. It exists only in
  memory while the request is processed. It never reaches a log line, a
  cookie, a database, or any Spotify artifact (playlist names and
  descriptions are fixed templates). The analytics database schema
  **contains no free-text columns**, so there is no place vent text
  *could* be written — a constraint pinned by automated tests, including
  a byte-level check that vent text never reaches the database file.
- **No identity:** no accounts, no user IDs, no IP addresses in
  analytics. Events cannot be attributed to a person, by us or anyone
  else.
- **What is stored** (anonymous event rows, one per action):
  a timestamp; the event type (`vent`, `rating`, `playlist_created`, or
  `crisis_declined`); the strategy chosen; the rating value; the number
  of tracks; and processing latency. Nothing else.
- Saved playlists are created **private** on the tester's own account.

## The beta and its objective

A 14-day, ~25-person beta with success criteria fixed in advance (so the
goalposts can't move after the data arrives):

1. **Return:** at least 40% of testers come back for a second session
   within 14 days.
2. **Perceived efficacy:** mean rating above +0.5 across at least 30
   rated sessions.
3. **The explanation lands:** in follow-up conversations, at least half
   of testers describe the one-line reasoning as accurate to where they
   were.

If the criteria hold, Venti earns further development; if not, the data
identifies which assumption failed. We note plainly that the rating is a
single-item self-report of perceived helpfulness — a product signal, not
a validated clinical outcome measure, and we don't present it as one.

## What we're asking of you

The metrics above can't answer the questions that matter most, which is
why you're being asked rather than a general audience:

1. **Use it as a person, not an auditor**, at least twice over the two
   weeks, on real moments — and tap the rating each time.
2. **Strategy calibration:** did the strategy it chose ever feel wrong or
   counterproductive for the state you described?
3. **Crisis calibration:** is the triage line drawn in a defensible
   place? Is the crisis screen's wording and resource choice right? Would
   you change what a person in that moment sees?
4. **Framing:** does the product communicate its non-clinical scope
   honestly, in the interface and in this document?

A 15-minute conversation near the end of the window covers all of this.
Criticism is the deliverable — a concern raised now is worth far more
than one discovered after the beta.

---

*The application is open source; every claim above about storage,
logging, and crisis behavior can be checked in the code and its tests.
Questions at any point are welcome.*
