"""
Emotion inference: vent text → (current VA, target VA, MMR strategy).

Inference runs through a pluggable LLMBackend (see web/app/llm): the `claude`
CLI for free local dev on a Max plan, or the Anthropic API for hosting. The
prompt encodes the psychology research so the model acts as a trained
mood-regulation reasoner, not a generic sentiment classifier.
"""
from .models import EmotionState, MMRStrategy
from .llm.base import LLMBackend, LLMError, extract_json, get_backend


INFERENCE_PROMPT_TEMPLATE = """You are an emotion-inference engine grounded in music psychology research.

Given a user's "vent" — a short message about how they're feeling and why —
output a JSON object describing their emotional state and the best music
intervention strategy.

You use two frameworks:

1. RUSSELL'S CIRCUMPLEX MODEL — emotions as 2D coordinates:
   - valence: -1.0 (very negative) to +1.0 (very positive)
   - arousal: -1.0 (very calm/low energy) to +1.0 (very intense/high energy)

   Frustration = negative valence, HIGH arousal (NOT the same as sadness)
   Sadness     = negative valence, LOW arousal
   Anger       = negative valence, very high arousal
   Boredom     = slightly negative valence, very low arousal
   Calm focus  = slight positive valence, low arousal
   Excitement  = positive valence, high arousal

2. SAARIKALLIO'S MMR — seven mood-regulation strategies:
   - entertainment: sustain an existing GOOD mood (only when valence is already positive)
   - revival: restore depleted energy, gentle lift after stress
   - strong_sensation: seek intense emotional experience, peak it
   - diversion: orthogonal escape — different topic entirely, NOT iso principle
   - discharge: cathartic release — let the negative emotion OUT (e.g. angry music for anger)
   - mental_work: contemplate, process, reappraise — for stuck rumination
   - solace: comfort, feel understood — for loneliness, grief, isolation

STRATEGY SELECTION RULES (these are the moat — be precise):
- Coding/work frustration with high arousal → DISCHARGE first, then shift
- Sadness from setback → SOLACE (don't jump to happy music; iso principle)
- Tired or energy-depleted after exertion → REVIVAL (gentle lift to restore)
- Bored, understimulated, or restless with nothing to do → ENTERTAINMENT or STRONG_SENSATION (add novelty and interest, do not just lift energy)
- Stuck in ambivalence, conflicted self-questioning, or unresolved existential disconnect (user is grappling with something, not just depleted by it) → MENTAL_WORK (sit with it and process rather than fix it)
- Stuck overthinking → MENTAL_WORK or DIVERSION depending on whether they want to process or escape
- Already happy, want to maintain → ENTERTAINMENT
- Anxious, racing thoughts → REVIVAL with calming target
- Sustained anger at external thing → DISCHARGE

ISO PRINCIPLE — for negative starting states, target should be ONE STEP toward
neutral/positive, not jumping straight to euphoric. The trajectory generator
will fill in waypoints; you just set start and target.

Output STRICT JSON with this exact shape and NOTHING ELSE — no markdown, no
code fences, no explanation outside the JSON, no preamble:
{{
  "current_valence": float,
  "current_arousal": float,
  "target_valence": float,
  "target_arousal": float,
  "strategy": "one of: entertainment, revival, strong_sensation, diversion, discharge, mental_work, solace",
  "reasoning": "2-3 sentences explaining why this strategy fits THIS context"
}}

VENT: {vent_text}

CONTEXT (what they're working on, recent themes): {context}"""


class InferenceError(RuntimeError):
    """Raised when the model's response is missing keys or fails validation."""


class EmotionInference:
    """
    Emotion inference over a pluggable LLM backend.

    Routes the inference prompt through an LLMBackend (the `claude` CLI or the
    Anthropic API). Pass a backend explicitly for testing / dependency
    injection; by default it's chosen from the LLM_BACKEND env var via
    get_backend().
    """

    def __init__(self, backend: LLMBackend | None = None):
        self.backend = backend if backend is not None else get_backend()

    def infer(self, vent_text: str, context: str = "") -> dict:
        """
        Returns dict with: current_emotion, target_emotion, strategy, reasoning.

        On a parse or validation failure the call is retried once; if the second
        attempt also fails, the error is raised. Backend transport errors (a
        timeout or auth failure) propagate immediately — a retry won't fix them.
        """
        prompt = INFERENCE_PROMPT_TEMPLATE.format(
            vent_text=vent_text,
            context=context or "none provided",
        )

        last_err = None
        for _ in range(2):  # initial attempt + one retry on bad/unparseable output
            raw = self.backend.complete(prompt)
            try:
                return self._parse(raw)
            except (InferenceError, LLMError) as e:
                last_err = e
        raise last_err

    def _parse(self, raw: str) -> dict:
        """Parse + validate one raw response. Raises InferenceError / LLMError."""
        parsed = extract_json(raw)

        # Validate required keys
        required = {"current_valence", "current_arousal", "target_valence",
                    "target_arousal", "strategy", "reasoning"}
        missing = required - parsed.keys()
        if missing:
            raise InferenceError(
                f"Claude Code response missing keys: {missing}\nGot: {parsed}"
            )

        try:
            strategy = MMRStrategy(parsed["strategy"])
        except ValueError:
            raise InferenceError(
                f"Unknown strategy: {parsed['strategy']!r}. "
                f"Expected one of: {[s.value for s in MMRStrategy]}"
            )

        return {
            "current_emotion": EmotionState(
                valence=float(parsed["current_valence"]),
                arousal=float(parsed["current_arousal"]),
            ),
            "target_emotion": EmotionState(
                valence=float(parsed["target_valence"]),
                arousal=float(parsed["target_arousal"]),
            ),
            "strategy": strategy,
            "reasoning": parsed["reasoning"],
        }
