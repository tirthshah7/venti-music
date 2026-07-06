# Venti Eval Pack — API Backend Runs (T1.3 gate)

_Backend: `LLM_BACKEND=api` (Anthropic SDK) · model: `claude-sonnet-4-6` · 15 scenarios · Gate: ≥14/15_
_Path under test: two-call `EmotionInference` (used by run_eval.py) — the merged `run_vent` pipeline is scored separately under T1.4._

---

## Run 2 (post retry-fix, 2026-07-06): 15/15 — GATE MET ✅

After adding retry-once to the two-call inference path (`EmotionInference` /
`QueryGenerator` — **code only, prompts untouched**), the pack re-ran clean.

| # | Scenario | Expected | API picked | Verdict |
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

---

## Run 1 (pre-fix, 2026-07-06): 13/15 — GATE NOT MET

Two misses, different in kind:

- **Scenario 1 — format failure.** Correct strategy (discharge) but the JSON
  omitted `target_valence`/`target_arousal` → `InferenceError` (missing keys).
  The two-call path had no retry. **This is what the retry fix addresses.**
- **Scenario 11 — chose solace** (out of the expected {revival, mental_work}).

---

## Honest caveats (what the fix did and did NOT do)

- **Scenario 1 is a real fix.** The failure was an incomplete-JSON slip with the
  correct strategy; retry-once directly addresses that failure mode (covered by a
  unit test, and confirmed by the clean re-run).
- **Scenario 11 is model variance, NOT a fix.** In Run 1 the model returned a
  valid, complete `solace` response — so no retry triggered; retry cannot change a
  validation-passing answer. In Run 2 the same input produced `mental_work`. The
  strategy choice for this scenario is non-deterministic on the API backend and
  can land in or out of the expected set on any given run. Per pre-committed
  policy, neither the prompt nor the expected-strategy set was changed.

### Scenario 11 reasoning, verbatim from each run

**Run 1 — solace:**
> This isn't frustration or rumination to fix — it's the physical dread of doing something ethically necessary but emotionally painful, and the user needs to feel that the weight they're carrying is understood rather than escaped. Solace steadies the nausea and offers companionship through an unavoidable hard moment, gently easing arousal without pretending the situation is fine. The iso-matched target moves toward calm acceptance rather than false positivity.

**Run 2 — mental_work:**
> The user isn't just depleted or angry — they're caught between what they know is right logically and a visceral guilt reaction, an unresolved internal conflict that needs processing rather than fixing. Mental_work supports sitting with the ambivalence and steadying their resolve before a hard duty. The target eases the physical dread (lowering arousal) and nudges valence toward acceptance without falsely brightening a genuinely heavy moment.
