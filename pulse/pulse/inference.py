"""
Emotion inference: vent text → (current VA, target VA, MMR strategy).

Uses Claude Code (`claude -p`) in headless mode as the inference engine,
which means inference runs against the user's Max plan rather than API
credits. The prompt encodes the psychology research so Claude acts as a
trained mood-regulation reasoner, not a generic sentiment classifier.

Trade-offs vs direct API:
- Pro: free under Max plan, no API key needed
- Pro: same model quality as API
- Con: slightly higher latency (subprocess startup ~1-2s)
- Con: requires `claude` CLI installed and authenticated
"""
import json
import shutil
import subprocess

from .models import EmotionState, MMRStrategy


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


class ClaudeCodeNotFoundError(RuntimeError):
    """Raised when the `claude` CLI is not installed or not on PATH."""


class InferenceError(RuntimeError):
    """Raised when Claude Code returns something we can't parse."""


class EmotionInference:
    """
    Emotion inference using Claude Code as the LLM transport.

    Calls `claude -p <prompt>` which runs in headless (print) mode,
    returning the model's response to stdout. No API key needed —
    auth is handled by Claude Code's existing login.
    """

    def __init__(self, claude_binary: str | None = None):
        self.claude_binary = claude_binary or shutil.which("claude")
        if not self.claude_binary:
            raise ClaudeCodeNotFoundError(
                "Could not find `claude` CLI on PATH. "
                "Install Claude Code from https://docs.claude.com/claude-code "
                "and run `claude login` first."
            )

    def infer(self, vent_text: str, context: str = "") -> dict:
        """
        Returns dict with: current_emotion, target_emotion, strategy, reasoning.
        Raises InferenceError if Claude Code's output can't be parsed.
        """
        prompt = INFERENCE_PROMPT_TEMPLATE.format(
            vent_text=vent_text,
            context=context or "none provided",
        )

        # Run claude -p in headless mode. The prompt goes in via stdin to
        # avoid command-line length limits and shell escaping issues.
        try:
            result = subprocess.run(
                [self.claude_binary, "-p"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise InferenceError("Claude Code timed out after 60 seconds.")
        except subprocess.CalledProcessError as e:
            raise InferenceError(
                f"Claude Code exited with code {e.returncode}.\n"
                f"stderr: {e.stderr}\n"
                f"Run `claude login` if this is an auth issue."
            )

        raw = result.stdout.strip()
        parsed = self._extract_json(raw)

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

    @staticmethod
    def _extract_json(raw: str) -> dict:
        """
        Robustly pull a JSON object out of Claude's response.

        Claude Code in -p mode usually returns clean JSON when prompted,
        but it sometimes wraps it in markdown fences or adds preamble.
        We handle both cases.
        """
        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # drop opening fence
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]  # drop closing fence
            text = "\n".join(lines).strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fallback: find the first {...} block
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise InferenceError(
                f"Could not find JSON object in Claude Code response:\n{raw!r}"
            )

        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as e:
            raise InferenceError(
                f"Failed to parse JSON from Claude Code response: {e}\n"
                f"Raw output:\n{raw!r}"
            )
