# Venti Eval Pack — Merged Pipeline (run_vent) on API Backend — T4.3

_Run date: 2026-07-06_
_Pipeline: merged single-call `run_vent()` (`venti_core/llm/vent_pipeline.py`)_
_Backend: `LLM_BACKEND=api` (Anthropic SDK) · model: `claude-opus-4-8` (from `.env` — note: the T1.4 baseline ran on `claude-sonnet-4-6`) · 15 scenarios · Gate: ≥14/15_
_Invocation: `evals/run_eval.py --pipeline merged`_
_Supersedes the T1.4 record (same file path, see git history)._

## What changed since T1.4

T4.3 added a voice instruction to the merged prompt's **bridge text** (the
`reasoning` field description in `_MERGED_TAIL`): reasoning must address the
person directly as 'you' (second person), never 'the user', never third
person. The reveal screen (Phase 4) displays reasoning as the headline — it
must speak *to* the person, not about them. The sliced-verbatim rule blocks
were not touched; `inference.py` and `query_generator.py` verified
byte-identical to HEAD before this run.

## Result: 15/15 — GATE MET ✅ (and 15/15 second-person voice)

| # | Scenario | Expected | run_vent picked | Verdict | Voice |
|---:|---|---|---|---|---|
| 1 | Sustained work frustration | discharge | discharge | PASS | you ✓ |
| 2 | Acute grief | solace | solace | PASS | you ✓ |
| 3 | Performance anxiety | revival / mental_work | revival | PASS | you ✓ |
| 4 | Sustained low energy | revival | revival | PASS | you ✓ |
| 5 | Productive flow | entertainment | entertainment | PASS | you ✓ |
| 6 | Existential rumination | mental_work / solace | mental_work | PASS | you ✓ |
| 7 | New parent overwhelm | revival / solace | revival | PASS | you ✓ |
| 8 | Social rejection | solace | solace | PASS | you ✓ |
| 9 | Hindi loneliness | solace | solace | PASS | you ✓ |
| 10 | Saturday boredom | entertainment / strong_sensation | entertainment | PASS | you ✓ |
| 11 | Pre-firing dread | revival / mental_work | mental_work | PASS | you ✓ |
| 12 | Joyful pre-wedding nerves | revival / entertainment | revival | PASS | you ✓ |
| 13 | Post-burnout return | mental_work / solace | mental_work | PASS | you ✓ |
| 14 | Rage at vendor | discharge | discharge | PASS | you ✓ |
| 15 | Caregiver depletion | solace / mental_work | solace | PASS | you ✓ |

**Score: 15/15.** Every strategy choice matches the T1.4 merged run exactly —
the voice instruction shifted tone, not judgment. Voice was graded
mechanically (second-person markers present, "the user"/"the person" absent)
across all 15 reasoning lines; per-scenario detail in `scenario_01..15.txt`.

Scenario 11 (pre-firing dread) again landed `mental_work` (in-set), as in the
T1.4 merged run. Its dual-defensible history is documented in the T1.4 record.

## Sample reasoning voice (scenario 2, acute grief — verbatim)
> Losing your dad is a profound grief, and right now you don't need to be
> lifted out of it or fixed — you need to feel held and understood. This music
> won't rush you toward feeling okay; it will simply sit beside you in the
> ache, gently, so you're not so alone in it tonight. Take it slow, and be
> kind to yourself.
