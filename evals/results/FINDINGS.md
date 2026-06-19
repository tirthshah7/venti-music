# Pulse Eval Pack — Deep Findings

_Analysis date: 2026-06-19_
_Based on: 15 eval-pack scenarios run through inference + trajectory pipeline_

---

## 1. Headline result

**12 PASS / 3 PARTIAL / 0 FAIL / 0 crashes**

Per the eval pack's own rubric, 12+ PASS means "v0's strategy selection is in good shape. Whatever failures show up are edge cases worth tracking but not blockers for open-sourcing."

The zero-FAIL count is notable. Pulse never made a *dangerous* recommendation — it never prescribed discharge for grief, never forced positivity on someone in acute pain, never misread anger as sadness. The PARTIALs are all cases where Pulse picked a *defensible alternative* rather than the *optimal* choice, or where the trajectory implementation undermined a reasonable strategy pick.

This is a v0 that is safe to ship and iterate on. The failure modes are taste-level, not safety-level.

---

## 2. Strategy bias analysis

### What Pulse actually picked vs. what was expected

| Strategy | Times picked | Times expected (primary) | Times expected (acceptable) | Delta |
|---|---:|---:|---:|---|
| solace | 5 | 4 | 7 | Slightly over-picked, but always appropriate when chosen |
| revival | 4 | 1 | 5 | **Over-picked** — 2 of 4 picks were PARTIALs |
| discharge | 2 | 2 | 2 | Perfectly calibrated |
| entertainment | 2 | 1 | 3 | Correct when picked, but once picked when revival was better (scenario 12) |
| mental_work | 2 | 1 | 5 | **Under-picked** — available in 5 scenarios, chosen in only 2 |
| strong_sensation | 0 | 0 | 1 | Never picked, acceptable once (scenario 10) |
| diversion | 0 | 0 | 0 | Never expected, never picked — not tested by this pack |

### Key biases

**Revival is the default "I don't know" strategy.** When Pulse encounters a low-energy, mildly negative state and isn't sure whether to process or energize, it defaults to revival. This happened in scenarios 10 (boredom) and 13 (post-burnout apathy). The prompt's rule "Boredom or low energy → REVIVAL" is the culprit — it's too broad a bucket.

**Mental_work is under-selected.** It was acceptable in 5 scenarios (3, 6, 11, 13, 15) but only chosen twice. The LLM seems to reach for mental_work only when the vent explicitly signals *thinking* ("i keep thinking about whether..."). For scenarios where the user is in an ambivalent or conflicted state without using thinking-words (scenario 13: "don't want to be here, don't want to be anywhere else"), the LLM doesn't connect that to contemplation/reappraisal.

**Discharge is well-calibrated — not over-prescribed.** This was a key concern in the eval pack ("watch for overprescription"). Pulse correctly limited discharge to the two scenarios with genuine external-facing anger/frustration and avoided it for anxiety (scenario 3), dread (scenario 11), and suppressed grief (scenario 15). This is the strongest signal that the prompt's strategy rules are working.

**Strong_sensation and diversion are untested.** Neither was the primary expected answer for any scenario. The eval pack should add scenarios that specifically call for these strategies — e.g., "I want to feel something intense" (strong_sensation) or "I'm stuck in a loop and need to break out" (diversion).

---

## 3. Emotional register blind spots

### Mixed valence (positive + anxious) — PARTIAL blind spot

**Scenario 12 (pre-wedding nerves):** Pulse correctly read the positive valence but the entertainment strategy's trajectory implementation can't handle "keep valence positive while reducing arousal." The *inference* was fine — the *code* failed. This is a specific category the trajectory system wasn't designed for: positive states with excess arousal that needs reduction.

**Impact:** Any real user in a "happy but overstimulated" state will get a playlist that stays overstimulated. This is the highest-priority code fix.

### Under-arousal without sadness — systematic blind spot

**Scenarios 10 (boredom) and 13 (post-burnout):** Both are low-arousal, mildly negative states where Pulse defaulted to revival. The LLM's reasoning in both cases actually *named the right emotional state* ("understimulation", "apathy and disconnection") but then picked revival because the prompt rules funnel all low-energy states into the same bucket.

**Pattern:** Pulse conflates three distinct low-arousal states:
1. **Tired/depleted** → revival (restore energy) — correctly handled in scenario 4
2. **Bored/understimulated** → entertainment or strong_sensation (add novelty) — missed in scenario 10
3. **Apathetic/ambivalent** → mental_work (process the disconnection) — missed in scenario 13

This is the most actionable finding: one prompt rule change could fix two PARTIALs.

### Suppressed/regulated states — NO blind spot

**Scenarios 8, 11, 15:** All correctly handled. Pulse recognized "it's fine. it's not fine" as suppressed hurt, "logically I know it's right" as moral dread needing processing, and "holding it together" as caregiver grief needing permission to feel. The LLM's contextual reading of emotional regulation cues is strong.

### Positive states — NO blind spot

**Scenario 5:** Correctly identified productive flow and chose entertainment to sustain rather than shift. This was the eval pack's test of whether Pulse defaults to mood-*shifting* — it doesn't.

### Non-English text — NO blind spot

**Scenario 9 (Hindi):** Correctly parsed, correctly inferred loneliness + homesickness, correctly chose solace. The VA values (−0.60, −0.35) are in the right region. The eval pack only tested Hindi — other scripts (Arabic, CJK, etc.) remain untested but the underlying LLM's multilingual capability suggests they'd work similarly.

### Surface emotion ≠ best intervention — NO blind spot

**Scenario 11 (pre-firing dread):** This was the eval pack's hardest test. High arousal + negative valence *looks like* discharge territory, but the context (needing to walk into a hard conversation regulated) means discharge would be actively harmful. Pulse nailed this — picked mental_work with reasoning that explicitly referenced the need to arrive "grounded rather than rattled." The LLM is reading situational context, not just VA snapshot.

---

## 4. Trajectory shape issues

### Across the 12 PASSes: trajectories are solid

Spot-checking the PASS trajectories:

| Scenario | Strategy | Trajectory behavior | Assessment |
|---|---|---|---|
| 1 (frustration) | discharge | Amplifies to (−0.69, +0.65), then eases to (−0.10, +0.30) | Correct catharsis-then-release shape |
| 2 (grief) | solace | Smooth (−0.85→−0.50), stays negative throughout | Correct — never forces positivity |
| 3 (anxiety) | revival | Smooth downward arousal (+0.75→+0.35) with valence lift | Correct regulation curve |
| 7 (new parent) | solace | Drops arousal to −0.70, valence gently lifts | Contextually brilliant — invites sleep at 2am |
| 14 (rage) | discharge | Amplifies to (−0.86, +0.82), then steps down | Correct, and more aggressive amp than scenario 1 — appropriate for higher arousal start |

No trajectory in the PASS set pushed target valence inappropriately positive. The iso principle is consistently respected.

### The one trajectory bug: entertainment ignores target

**Scenario 12:** The `_entertainment_trajectory()` function generates waypoints by oscillating ±0.05 around the current state. It does not reference the target at all. The code:

```python
EmotionState(
    valence=current.valence + 0.05 * (i % 2 - 0.5),
    arousal=current.arousal + 0.05 * ((i + 1) % 2 - 0.5),
)
```

This means for scenario 12 (current arousal +0.85, target arousal +0.30), the trajectory stays at +0.82 to +0.88 — it never moves toward the target. The design assumption behind entertainment ("stay where you are, just sustain") breaks when the user is in a positive-valence state but needs arousal *reduction*.

This is not just a scenario-12 problem. Any future scenario where entertainment is chosen but the current and target differ significantly will produce a trajectory that ignores the intent.

### Trajectories for PARTIAL scenarios (10, 13): actually fine

Both used revival's iso-principle trajectory, which smoothly interpolates from current to target. The trajectories themselves are reasonable — the issue was strategy selection, not trajectory shape. If the strategy had been correct (entertainment for 10, mental_work for 13), the iso trajectory from mental_work would have produced a similar smooth shape, and entertainment's trajectory would have oscillated near current (which is actually what you'd want for boredom — stay in a stimulating zone).

---

## 5. The "expected answer was wrong" cases

### Scenario 10 (boredom): eval pack expectation is debatable

The eval pack expects entertainment or strong_sensation. Pulse picked revival. Honestly, this is a gray area.

**Case for the eval pack:** Boredom is understimulation. The user doesn't need *restoration* (they're not depleted from exertion), they need *stimulation*. Entertainment or strong_sensation provides novelty; revival provides gentle lift. You don't give a bored person a warm cup of tea — you give them something interesting.

**Case for Pulse:** The VA values Pulse inferred (−0.20 valence, −0.70 arousal) put this firmly in the "low energy" zone. Revival's gentle lift trajectory is reasonable. The user said "brain feels empty" which could read as depleted, not just bored.

**Verdict:** The eval pack is *more* right. "Brain feels empty" + "nothing planned" + "saturday afternoon" reads as understimulation, not exhaustion. But revival isn't *wrong* — it's just less precise.

### Scenario 13 (post-burnout): eval pack expectation is debatable

The eval pack expects mental_work or solace. Pulse picked revival.

**Case for the eval pack:** "Don't want to be here, don't want to be anywhere else either" is existential ambivalence. The user isn't tired — they're *disconnected*. Mental_work lets them sit with the ambivalence and process it. Revival tries to fix something the user hasn't asked to fix.

**Case for Pulse:** First day back from time off, low energy, flat affect. Revival is literally named "restore energy after stress." The LLM's reasoning calls it "flat, listless disconnection" and argues revival "gently restores engagement without forcing positivity."

**Verdict:** The eval pack is right, but Pulse's choice isn't harmful. The distinction between "I need energy" and "I need to process" is subtle enough that a human therapist might disagree with either answer. The problem is that the prompt rules make this decision for the LLM rather than letting it reason freely.

### Scenario 12 (pre-wedding nerves): Pulse's strategy choice is defensible

Entertainment is one of the two expected strategies. The issue is entirely in the trajectory code, not the inference. If `_entertainment_trajectory()` respected the target, this would be a clean PASS. I'd reclassify this as a code bug, not an inference failure.

---

## 6. Recommended prompt fixes

### Fix 1: Split the low-arousal rule into tired vs. bored vs. ambivalent

**Current rule (line 53 of inference.py prompt):**
> Boredom or low energy → REVIVAL (gentle lift)

**Proposed replacement:**
> Tired / energy-depleted after exertion → REVIVAL (gentle lift)
> Bored / understimulated / restless with nothing to do → ENTERTAINMENT or STRONG_SENSATION (add novelty and interest)
> Ambivalent / apathetic / emotionally flat without clear cause → MENTAL_WORK (sit with it and process)

**Expected impact:** Fixes scenarios 10 and 13. Does not risk breaking scenario 4 (tired) which would still match the first sub-rule.

### Fix 2: Add a "positive valence + high arousal" rule

**Current gap:** No rule addresses the case where valence is positive but arousal is too high. The LLM defaults to entertainment (positive valence → sustain) but the entertainment trajectory can't reduce arousal.

**Proposed addition:**
> Positive valence but excessive arousal (jittery, can't sit still, nervous excitement) → REVIVAL with target that preserves valence while lowering arousal. Do NOT use entertainment here — entertainment sustains the current state, and the current arousal level is the problem.

**Expected impact:** Fixes scenario 12 at the inference level (LLM picks revival instead of entertainment, so the iso trajectory naturally moves toward the lower-arousal target). This is an alternative to fixing the entertainment trajectory code — or you could do both.

### Fix 3: Add a "future event requiring regulation" contextual rule

**Current state:** The LLM correctly handled scenario 11 (pre-firing dread) but there's no explicit rule for it. It worked because the LLM's general reasoning is strong, but future similar scenarios (pre-surgery, pre-court-appearance, pre-difficult-conversation) might not all be caught.

**Proposed addition:**
> If the user describes a stressful event they need to face soon (within hours), prefer REVIVAL or MENTAL_WORK over DISCHARGE — they need to arrive regulated, not catharted. Discharge is for *after* the event or for anger at something that doesn't require an upcoming regulated response.

**Expected impact:** Hardens an existing strength. Low urgency — the LLM already handles this — but makes the reasoning explicit for prompt maintainability.

### Fix 4: Add examples to the prompt for ambiguous low-arousal states

The current prompt has strategy rules but no worked examples. Adding 2-3 brief examples at the boundary between revival/mental_work/entertainment for low-arousal states would help the LLM distinguish between them without requiring as much free reasoning.

**Proposed addition (after the strategy rules block):**
> DISAMBIGUATION EXAMPLES:
> - "just tired, long day" → revival (energy depleted, needs restoration)
> - "bored, nothing to do" → entertainment (understimulated, needs novelty)
> - "don't feel like doing anything, can't explain why" → mental_work (emotional flatness, needs processing)

**Expected impact:** Reinforces Fix 1 with concrete anchoring. LLMs are better at pattern-matching from examples than following abstract rules for edge cases.

### Fix 5: (Code, not prompt) Fix `_entertainment_trajectory()` to blend toward target

This is a trajectory.py change, not a prompt change, but it's the most impactful single fix for the eval results.

**Current behavior:** Entertainment trajectory oscillates ±0.05 around current state, ignoring target entirely.

**Proposed behavior:** When the distance between current and target exceeds a threshold (e.g., 0.3 in VA space), blend the oscillation toward the target over the waypoint sequence. When distance is small (the normal entertainment case — sustaining a good mood), behavior is unchanged.

**Expected impact:** Fixes scenario 12's trajectory. Also future-proofs entertainment for any case where the LLM correctly identifies a positive state but needs some arousal/valence adjustment.

---

## 7. Issues to file

### Issue 1: Strategy rules conflate boredom, tiredness, and apathy into one "low energy" bucket

**Labels:** `prompt-engineering`, `good first issue`

The inference prompt's strategy selection rules currently map "Boredom or low energy → REVIVAL." In eval testing, this caused Pulse to prescribe revival (energy restoration) for a bored user who needed entertainment (novelty/stimulation) and a post-burnout user who needed mental_work (processing ambivalence). These are three distinct low-arousal emotional states that call for different interventions. The fix is to split the rule into three sub-rules: tired/depleted → revival, bored/understimulated → entertainment or strong_sensation, ambivalent/flat → mental_work. Adding 2-3 disambiguation examples after the rules would further anchor the distinction. See eval scenarios 10 and 13 for test cases.

### Issue 2: Entertainment trajectory ignores target emotion entirely

**Labels:** `bug`, `trajectory`, `good first issue`

The `_entertainment_trajectory()` function in `trajectory.py` generates waypoints by oscillating ±0.05 around the current emotional state. It never references the target emotion at all. This is correct for the typical entertainment case (sustaining a good mood, where current ≈ target), but breaks when the LLM correctly identifies a positive-valence state that still needs arousal reduction — e.g., pre-wedding jitters where the user is happy but overstimulated. The trajectory stays at high arousal despite the LLM setting a lower arousal target. Fix: when the distance between current and target exceeds a threshold (e.g., 0.3 in VA space), blend the oscillation toward the target across the waypoint sequence. Eval scenario 12 is the reproduction case.

### Issue 3: No prompt rule for positive-valence, high-arousal states needing regulation

**Labels:** `prompt-engineering`, `enhancement`

The inference prompt has no explicit guidance for states where valence is positive but arousal is problematically high (nervous excitement, jittery anticipation, can't-sit-still energy). The LLM currently defaults to entertainment (because valence is positive), but entertainment's "sustain current state" design is wrong when the current *arousal level* is the problem. Adding a rule like "positive valence but excessive arousal → revival with target that preserves valence while lowering arousal" would direct the LLM toward a strategy whose trajectory actually moves toward the target. This is an alternative to (or complement of) fixing the entertainment trajectory. Eval scenario 12 (pre-wedding nerves) is the test case.

### Issue 4: Eval pack has no scenarios testing diversion or strong_sensation as primary expected strategies

**Labels:** `testing`, `eval-pack`, `good first issue`

The current 15-scenario eval pack never has diversion or strong_sensation as the primary expected strategy. This means we have no signal on whether Pulse correctly identifies contexts that call for these strategies. Suggested additions: (1) A "stuck in a rumination loop, tried processing, need to break out" scenario expecting diversion. (2) A "I want to feel something intense, everything feels muted" scenario expecting strong_sensation. (3) A "numb after a long stretch of routine, craving peak experience" scenario expecting strong_sensation. Without these, two of the seven MMR strategies are untested.

### Issue 5: Add future-event contextual rule to harden pre-event scenario handling

**Labels:** `prompt-engineering`, `enhancement`, `low priority`

Pulse correctly handled the "have to fire someone in an hour" scenario (chose mental_work over discharge), but this relied on the LLM's general reasoning rather than an explicit prompt rule. For robustness against future pre-event scenarios (pre-surgery anxiety, pre-court-appearance dread, pre-difficult-family-conversation), consider adding an explicit rule: "If the user describes a stressful event they need to face soon, prefer revival or mental_work over discharge — they need to arrive regulated, not catharted." This hardens an existing strength and makes the reasoning explicit for contributors who may modify the prompt. Low priority since the current behavior is already correct.
