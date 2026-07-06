# Venti Eval Pack — Merged Pipeline (run_vent) — PRODUCTION BASELINE — T4.5

**Model: `claude-sonnet-4-6` (set explicitly — the production model).**

_Run date: 2026-07-06_
_Pipeline: merged single-call `run_vent()` (`venti_core/llm/vent_pipeline.py`), including the T4.3 second-person voice instruction_
_Backend: `LLM_BACKEND=api` (Anthropic SDK) · `ANTHROPIC_MODEL=claude-sonnet-4-6` · 15 scenarios · Gate: ≥14/15_
_Invocation: `ANTHROPIC_MODEL=claude-sonnet-4-6 evals/run_eval.py --pipeline merged`_
_Supersedes as production baseline: T4.3 record (opus-4-8, 15/15) and T1.4 record (sonnet-4-6, pre-voice-instruction, 15/15) — both in git history at this path._

## Result: 14/15 — GATE MET ✅ · Voice 15/15 ✅

| # | Scenario | Expected | run_vent picked | Verdict | Voice |
|---:|---|---|---|---|---|
| 1 | Sustained work frustration | discharge | discharge | PASS | you ✓ |
| 2 | Acute grief | solace | solace | PASS | you ✓ |
| 3 | Performance anxiety | revival / mental_work | revival | PASS | you ✓ |
| 4 | Sustained low energy | revival | **mental_work** | **FAIL** | you ✓ |
| 5 | Productive flow | entertainment | entertainment | PASS | you ✓ |
| 6 | Existential rumination | mental_work / solace | mental_work | PASS | you ✓ |
| 7 | New parent overwhelm | revival / solace | revival | PASS | you ✓ |
| 8 | Social rejection | solace | solace | PASS | you ✓ |
| 9 | Hindi loneliness | solace | solace | PASS | you ✓ (Hindi, see note) |
| 10 | Saturday boredom | entertainment / strong_sensation | entertainment | PASS | you ✓ |
| 11 | Pre-firing dread | revival / mental_work | mental_work | PASS | you ✓ |
| 12 | Joyful pre-wedding nerves | revival / entertainment | revival | PASS | you ✓ |
| 13 | Post-burnout return | mental_work / solace | mental_work | PASS | you ✓ |
| 14 | Rage at vendor | discharge | discharge | PASS | you ✓ |
| 15 | Caregiver depletion | solace / mental_work | solace | PASS | you ✓ |

**Score: 14/15 (gate ≥14 met). Voice: 15/15.** Per-scenario detail in
`scenario_01..15.txt` alongside this file.

## Scenario 4 (sustained low energy) — the one miss

Expected `revival`, got `mental_work`. Sonnet read "just tired, nothing's
really wrong, going through motions" as low-grade existential drift wanting
reflection rather than restoration; the opus-4-8 run (T4.3) and the earlier
sonnet pre-voice run (T1.4) both chose `revival`. The reasoning is coherent
but out-of-set. **Per pre-committed policy, no prompt or expected-set change
was made** (same policy previously applied to scenario 11's solace/mental_work
variance — see the T1.4 record). Verbatim:

> You're not depleted by effort or crushed by grief — you're stuck in a kind
> of low-grade existential drift, going through motions without feeling
> connected to them. That ambivalence and quiet disconnection calls for music
> that sits with you in that space and gently helps you reflect on it, rather
> than cheerfully pulling you somewhere you don't feel.

Watch item: if scenario 4 misses again on a future sonnet run, that's a
prompt-level conversation (to be re-verified on both backends per build rule),
not an eval-set edit.

## Voice check (mechanical)

Second-person markers present and "the user"/"the person" absent in all 15
reasoning lines. Scenario 9 answers in Hindi and is fully second-person
("आप जो महसूस कर रहे हैं…"); the marker set includes Hindi second-person
pronouns (आप/तुम) — an English-only marker set under-counts this scenario.
