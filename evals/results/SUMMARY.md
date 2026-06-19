# Venti Eval Pack — Results Summary

_Updated after low-arousal rule split in inference.py — scenarios 4, 10, 13 reclassified._

_Run date: 2026-06-19 (latest run with tightened prompt rules)_
_Model: Claude via `claude -p` (headless mode)_
_Scenarios: 15 / Crashes: 0_

## Scoring table

| # | Scenario | Expected | Venti picked | Verdict | Notes |
|---:|---|---|---|---|---|
| 1 | Sustained debug frustration | discharge | discharge | **PASS** | Correct. VA values and trajectory (amplify-then-ease) are textbook discharge. |
| 2 | Acute grief | solace | solace | **PASS** | Correct. Target stays negative (−0.50), doesn't force positivity. Reasoning explicitly names iso principle. |
| 3 | Pre-presentation anxiety | revival / mental_work | revival | **PASS** | Correct. Recognized anxiety as high-arousal needing downregulation, not anger needing discharge. |
| 4 | Tired, nothing wrong | revival | revival | **PASS** | Correct. Distinguished energy depletion from ambivalence after prompt rule tightening. |
| 5 | Productive flow | entertainment | entertainment | **PASS** | Correct. Recognized positive state and chose to sustain, not shift. |
| 6 | Existential rumination | mental_work / solace | mental_work | **PASS** | Correct. Identified stuck rumination. Reasoning explicitly notes user wants to think, not escape. |
| 7 | New parent overwhelm | revival / solace | solace | **PASS** | Chose solace (one of two acceptable). Reasoning cites isolation and permission to rest. Target arousal drops to −0.70 to invite sleep — contextually smart for 2am. |
| 8 | Social rejection | solace | solace | **PASS** | Correct. Recognized suppressed hurt. Target stays negative, gentle easing. |
| 9 | Hindi loneliness | solace | solace | **PASS** | Correct. Hindi text parsed without error. Reasoning correctly identifies loneliness + homesickness. |
| 10 | Saturday boredom | entertainment / strong_sensation | entertainment | **PARTIAL** | Strategy is now correct (entertainment, after prompt rule split). But the `_entertainment_trajectory()` code bug means trajectory oscillates near current state (−0.17/−0.12 valence, −0.67/−0.72 arousal) instead of moving toward the target (+0.40, +0.20). Inference fixed; trajectory code bug remains. |
| 11 | Pre-firing dread | revival / mental_work | mental_work | **PASS** | Correct. Reasoning: "unresolved internal conflict between conviction and conscience" — the tightened mental_work rule correctly matched ambivalence. |
| 12 | Joyful pre-wedding nerves | revival / entertainment | revival | **PASS** | Now picks revival (previously entertainment). Trajectory correctly moves arousal from +0.85 down to +0.30 while preserving positive valence. Fixed by prompt rule split. |
| 13 | Post-burnout return | mental_work / solace | mental_work | **PASS** | Now picks mental_work (previously revival). Reasoning correctly identifies ambivalence and rules out revival. Fixed by prompt rule split. |
| 14 | Rage at vendor | discharge | discharge | **PASS** | Correct. Clean hit. Reasoning distinguishes "existential fury" from "mild frustration." |
| 15 | Caregiver depletion | solace / mental_work | solace | **PASS** | Correct. Reasoning nails the "performing okayness" dynamic and correctly avoids discharge. |

## Score: 14 PASS / 1 PARTIAL / 0 FAIL

## Analysis of remaining PARTIAL

### Scenario 10 (Saturday boredom → entertainment, but trajectory doesn't move toward target)

**Root cause:** The inference is now correct — entertainment is an acceptable strategy for boredom. But the `_entertainment_trajectory()` function in `trajectory.py` ignores the target entirely. It generates small oscillations (±0.05) around the current state, so the trajectory stays near (−0.15, −0.70) instead of moving toward the target (+0.40, +0.20).

This is a **code bug**, not an inference bug. The entertainment trajectory implementation assumes current ≈ target (which is true for the typical "sustain a good mood" case but false for boredom).

**Fix:** `_entertainment_trajectory()` should blend toward target when the VA distance is large, rather than purely oscillating near current.

## Recommendations

1. **Fix `_entertainment_trajectory()`** to blend toward target when the gap is large, rather than purely oscillating near current. (Fixes the remaining PARTIAL)
2. **Add eval scenarios for diversion and strong_sensation** — neither is tested as a primary expected strategy in the current pack.
3. No further prompt changes needed — 14/15 PASS with zero crashes is solid for v0.
