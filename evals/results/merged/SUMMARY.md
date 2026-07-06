# Venti Eval Pack — Merged Pipeline (run_vent) on API Backend — T1.4

_Run date: 2026-07-06_
_Pipeline: merged single-call `run_vent()` (`venti_core/llm/vent_pipeline.py`)_
_Backend: `LLM_BACKEND=api` (Anthropic SDK) · model: `claude-sonnet-4-6` · 15 scenarios · Gate: ≥14/15_
_Invocation: `evals/run_eval.py --pipeline merged`_

## Result: 15/15 — GATE MET ✅

| # | Scenario | Expected | run_vent picked | Verdict |
|---:|---|---|---|---|
| 1 | Sustained work frustration | discharge | discharge | PASS |
| 2 | Acute grief | solace | solace | PASS |
| 3 | Performance anxiety | revival / mental_work | revival | PASS |
| 4 | Sustained low energy | revival | revival | PASS |
| 5 | Productive flow | entertainment | entertainment | PASS |
| 6 | Existential rumination | mental_work / solace | mental_work | PASS |
| 7 | New parent overwhelm | revival / solace | revival | PASS |
| 8 | Social rejection | solace | solace | PASS |
| 9 | Hindi loneliness | solace | solace | PASS |
| 10 | Saturday boredom | entertainment / strong_sensation | entertainment | PASS |
| 11 | Pre-firing dread | revival / mental_work | mental_work | PASS |
| 12 | Joyful pre-wedding nerves | revival / entertainment | revival | PASS |
| 13 | Post-burnout return | mental_work / solace | mental_work | PASS |
| 14 | Rage at vendor | discharge | discharge | PASS |
| 15 | Caregiver depletion | solace / mental_work | solace | PASS |

**Score: 15/15.**

Both pipelines now pass the gate at 15/15 on the API backend:
- **two-call** (`EmotionInference` + trajectory) — see `../SUMMARY_api_backend.md`.
- **merged** (`run_vent`, this file) — one LLM call that additionally returns the 4
  search queries. Per-scenario detail in `scenario_01..15.txt` alongside this file.

Note: scenario 11 (pre-firing dread) is a scenario whose strategy varies on the API
backend between `solace` and `mental_work` (both defensible). It landed on
`mental_work` (in-set) in this merged run and in the two-call re-run; it landed on
`solace` (out-of-set) in the first two-call run. No prompt or expected-set change was
made — per pre-committed policy.

## Scenario 11 (pre-firing dread) — merged-run reasoning, verbatim
> This isn't simple sadness or frustration — you're grappling with a conflict between what you know is right and how it feels, sitting with anticipatory dread and moral weight. Mental_work lets you contemplate and steady yourself rather than suppress or distract, moving from queasy tension toward a grounded, resolved calm before you act.
