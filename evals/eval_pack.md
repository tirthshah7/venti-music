# Pulse prompt evaluation pack

A set of 15 diverse hypothetical vent scenarios for testing whether Pulse's
emotion inference and strategy selection generalize beyond the specific
voice and contexts of its creator.

## How to use

For each scenario below:

1. Run `vent --dry-run "<vent text>" --context "<context>"` so no music actually plays.
2. Read the inferred strategy and reasoning printed by Pulse.
3. Compare against the "expected strategy" notes in the scenario.
4. Mark the result in the scoring sheet at the bottom.

Don't worry if some are wrong — the goal is to identify systematic failure
modes, not pass every case. A v0 that passes 10/15 is healthier than one
that overfits to the test set.

This pack is meant to be open-source-friendly: contributors can add their
own scenarios, especially ones representing emotional registers that
this initial set under-represents (cultural variation, age range,
neurodivergent framing, etc.).

---

## Scenarios

### 1. Sustained work frustration (peer to creator's own contexts)
**Vent:** "third hour debugging this kafka thing and i can't even tell what's broken anymore"
**Context:** "backend work"
**Expected strategy:** discharge (high arousal frustration with mounting irritation)
**Watch for:** Overprescription — if v0 keeps prescribing discharge for *every* coding vent, it's not really reading context. A user this fried might actually benefit from diversion (escape the loop) or mental_work (step back and process).

### 2. Acute grief
**Vent:** "my dad died last night. flying home tomorrow morning. i don't know what to do with myself right now."
**Context:** ""
**Expected strategy:** solace (negative valence, low-to-mid arousal, needs comfort not catharsis)
**Watch for:** If v0 picks discharge or revival here, the prompt is broken. Solace is the only correct choice. Also watch the trajectory — target valence should NOT be strongly positive. Forcing someone in acute grief toward happy music is the canonical iso-principle failure case.

### 3. Performance anxiety (peak arousal, future-facing)
**Vent:** "presentation in 20 minutes, hands shaking, can't remember any of my opening lines"
**Context:** "important client meeting"
**Expected strategy:** revival (calm down) or possibly mental_work (focus and prepare)
**Watch for:** Discharge would be wrong here — adding aggressive music to existing high arousal could make it worse. The target arousal must move *down* from current.

### 4. Sustained low energy (different from sadness)
**Vent:** "i don't know, just tired. nothing's really wrong. just kind of going through motions."
**Context:** "tuesday afternoon"
**Expected strategy:** revival (gentle lift, low arousal → mid arousal)
**Watch for:** Solace would be a misread — this isn't grief, it's energy depletion. Discharge would be a misread — there's no anger to release. Entertainment would suggest the LLM hasn't noticed valence is negative.

### 5. Productive flow (already in a good state)
**Vent:** "got the schema migration working, feeling like i can take on the rest of this sprint"
**Context:** "good momentum, mid-afternoon"
**Expected strategy:** entertainment (sustain existing positive mood) or possibly strong_sensation
**Watch for:** If v0 picks revival or solace here, it's defaulting to mood-shifting interventions even when no shift is needed. Entertainment is the test of whether the LLM recognizes positive states.

### 6. Existential rumination
**Vent:** "i keep thinking about whether i should be doing something more meaningful with my life. been on this for weeks. can't shake it."
**Context:** "late evening, alone"
**Expected strategy:** mental_work (contemplation and processing) or solace
**Watch for:** Diversion would be wrong here — the user explicitly wants to *think*, not escape. Discharge would be wrong — there's no acute frustration. This is a test of whether the LLM distinguishes thinking-mode emotional states from acute-emotion states.

### 7. New parent overwhelm
**Vent:** "haven't slept more than three hours in a row in a month. baby just went down. i should be sleeping but i'm staring at the ceiling."
**Context:** "2am, kid asleep"
**Expected strategy:** revival (restore energy gently) or solace
**Watch for:** This is an under-arousal state, not negative-affect anger. The trajectory should move toward calm, not toward intensity. Tests whether v0 conflates "stressed" with "high arousal."

### 8. Social rejection (interpersonal, not professional)
**Vent:** "she said she just wants to be friends. it's fine. it's not fine."
**Context:** ""
**Expected strategy:** solace (negative valence, low arousal, needs companionship not energy)
**Watch for:** Discharge here would be a clinically known anti-pattern — angry-breakup music can prolong negative rumination rather than process it. Solace is the safe and research-supported choice.

### 9. Cultural / language disconnect (testing non-Western framing)
**Vent:** "मुझे आज बहुत अकेलापन लग रहा है, घर वालों की बहुत याद आ रही है"
**Context:** "missing home"
**Expected strategy:** solace
**Watch for:** Does the LLM correctly infer emotional state from Hindi? Does it recognize loneliness + family-longing as a solace context? If it fails on language, that's a flag for Pulse needing explicit multilingual support before any non-English open-source distribution.

### 10. Boredom (positive-leaning, low arousal)
**Vent:** "saturday afternoon, nothing planned, brain feels empty"
**Context:** "weekend"
**Expected strategy:** entertainment or strong_sensation (need stimulation, not regulation)
**Watch for:** Solace would be wrong — there's no negative emotion to soothe. Revival might also misfire — the user isn't depleted, they're under-stimulated. This tests whether v0 distinguishes "needs energy" from "needs intensity."

### 11. Pre-confrontation arousal
**Vent:** "have to fire someone in an hour. logically i know it's the right call. i feel sick."
**Context:** "management duties"
**Expected strategy:** revival (calm the somatic anxiety) or mental_work (steady focus)
**Watch for:** This is high arousal + negative valence, but discharge would be deeply wrong — this person needs to walk into a hard conversation regulated, not amped up. Tests whether the LLM reads situational context (what's about to happen) and not just emotional snapshot.

### 12. Joyful but anxious anticipation
**Vent:** "wedding in two days. happy but also losing my mind. can't sit still."
**Context:** "personal milestone"
**Expected strategy:** revival (channel arousal down without killing positive valence) or entertainment
**Watch for:** This is a mixed-valence state. Discharge would be wrong — the arousal isn't anger. Solace would be wrong — the valence isn't negative. The LLM has to honor both signals.

### 13. Recovery from burnout
**Vent:** "first day back after a week off. don't want to be here. don't want to be anywhere else either."
**Context:** "back at work"
**Expected strategy:** mental_work or solace
**Watch for:** This is low arousal + low motivation + low valence. Revival would be premature — the user isn't ready to be lifted. Tests for whether v0 over-prescribes upward-trajectory interventions.

### 14. Rage at a specific external event
**Vent:** "stripe just held our payouts again, third time this quarter, support is useless"
**Context:** "founder, cash flow stressed"
**Expected strategy:** discharge
**Watch for:** This *is* a discharge case — and a clean one. If v0 misses this, the strategy selection is broken in a way that matters. Compare the trajectory to scenario 1's — the contexts feel similar but the underlying emotion (acute external anger vs. sustained internal frustration) calls for different waypoint shapes.

### 15. Caregiver depletion
**Vent:** "mom's chemo round three tomorrow. i'm holding it together for her but i'm not really holding it together."
**Context:** "caregiver"
**Expected strategy:** solace (acknowledge the suppressed grief without forcing release) or mental_work
**Watch for:** Discharge would be inappropriate — the user is actively suppressing emotion to function, and forcing catharsis right now could destabilize that. Solace honors the state without pushing. This tests whether the LLM picks up the "holding it together" cue as a signal NOT to disrupt.

---

## Scoring sheet

For each scenario, mark one:

- **PASS** — strategy and trajectory direction match expectation
- **PARTIAL** — strategy reasonable but trajectory direction off, OR strategy plausible alternative
- **FAIL** — strategy clearly wrong for the context

| # | Vent (short) | Expected strategy | Pulse picked | Verdict | Notes |
|---:|---|---|---|---|---|
| 1 | sustained debug frustration | discharge / diversion | | | |
| 2 | acute grief | solace | | | |
| 3 | pre-presentation anxiety | revival / mental_work | | | |
| 4 | tired but nothing wrong | revival | | | |
| 5 | productive flow | entertainment | | | |
| 6 | existential rumination | mental_work / solace | | | |
| 7 | new parent insomnia | revival / solace | | | |
| 8 | social rejection | solace | | | |
| 9 | Hindi loneliness | solace | | | |
| 10 | saturday boredom | entertainment / strong_sensation | | | |
| 11 | pre-firing dread | revival / mental_work | | | |
| 12 | joyful pre-wedding nerves | revival / entertainment | | | |
| 13 | post-burnout return | mental_work / solace | | | |
| 14 | rage at vendor | discharge | | | |
| 15 | caregiver suppression | solace / mental_work | | | |

## What to do with the results

After completing the pack:

**12+ PASS:** v0's strategy selection is in good shape. Whatever failures show up are edge cases worth tracking but not blockers for open-sourcing.

**8-11 PASS:** There's a systematic bias somewhere. Look at the FAILs as a group — do they cluster around one strategy being over-picked? Around one emotional register (e.g., always missing under-arousal states)? That's your highest-leverage prompt fix.

**Below 8 PASS:** The strategy selection rules in the inference prompt need real work before public release. Strangers will hit these failure modes immediately. Worth a focused weekend on tightening the prompt's strategy decision tree before sharing the repo.

## What this pack does NOT test

- Trajectory smoothness (waypoint-to-waypoint coherence)
- Search query quality (whether the LLM's queries find good Spotify matches)
- Personalization over time (impossible without longitudinal data)
- Cultural appropriateness of music selection (different question from strategy selection)

Those need their own evaluation work. This pack focuses narrowly on the
first decision in the pipeline — does the LLM correctly read the emotional
state — because that's the upstream gate. If strategy selection is wrong,
nothing downstream can save it.
