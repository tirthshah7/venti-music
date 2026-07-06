"""
Merged single-call vent pipeline for the hosted web path.

The CLI makes two LLM calls (emotion inference, then query generation). For the
web flow we do it in ONE call: run_vent() sends a merged prompt — the exact
psychology rules from the inference prompt plus the exact query-style rules from
the query prompt, sliced verbatim from the source templates so they can't drift —
and asks for emotion + strategy + reasoning + 4 queries as a single JSON object.

The model is only told to *assume* a standard 4-waypoint ISO arc when writing
queries; the real trajectory for display is still computed server-side with
venti_core.trajectory.generate_trajectory.
"""
from dataclasses import dataclass

from ..models import EmotionState, MMRStrategy
from ..trajectory import generate_trajectory
from ..inference import INFERENCE_PROMPT_TEMPLATE
from ..query_generator import QUERY_PROMPT_TEMPLATE
from .base import LLMBackend, LLMError, extract_json


class VentPipelineError(LLMError):
    """Raised when the merged response can't be parsed or fails validation."""


# --- Merged prompt -----------------------------------------------------------
# Slice the rule blocks straight out of the two source templates so the
# psychology + query-style rules stay character-for-character identical to the
# prompts the CLI path uses (no retyping, no drift).
_PSYCH_RULES = INFERENCE_PROMPT_TEMPLATE[
    INFERENCE_PROMPT_TEMPLATE.index("You use two frameworks:"):
    INFERENCE_PROMPT_TEMPLATE.index("\n\nOutput STRICT JSON")
]
_QUERY_RULES = QUERY_PROMPT_TEMPLATE[
    QUERY_PROMPT_TEMPLATE.index("Search query rules:"):
    QUERY_PROMPT_TEMPLATE.index("\n\nOutput STRICT JSON")
]

_MERGED_HEAD = """You are an emotion-inference engine AND a music search-query generator,
grounded in music psychology research.

Given a user's "vent" — a short message about how they're feeling and why —
do BOTH of the following in one step: (a) infer their current and target
emotional state and the best mood-regulation strategy, and (b) generate Spotify
search queries for a short playlist that carries out that strategy.

"""

_MERGED_MID = """

For the playlist, assume a standard 4-waypoint ISO-shaped arc from the current
state to the target state — four songs that move gradually from where the user
is toward where they should go. Produce ONE short Spotify search query per
waypoint: exactly 4 queries, ordered from the waypoint nearest the current state
to the waypoint nearest the target.

"""

_MERGED_TAIL = """

Output STRICT JSON with this exact shape and NOTHING ELSE — no markdown, no
code fences, no explanation outside the JSON, no preamble:
{
  "current_valence": float,
  "current_arousal": float,
  "target_valence": float,
  "target_arousal": float,
  "strategy": "one of: entertainment, revival, strong_sensation, diversion, discharge, mental_work, solace",
  "reasoning": "2-3 sentences explaining why this strategy fits THIS context — spoken directly to the person as 'you' (second person); never 'the user', never third person",
  "queries": ["query 1", "query 2", "query 3", "query 4"]
}"""

MERGED_PROMPT_TEMPLATE = _MERGED_HEAD + _PSYCH_RULES + _MERGED_MID + _QUERY_RULES + _MERGED_TAIL


@dataclass
class VentResult:
    current_emotion: EmotionState
    target_emotion: EmotionState
    strategy: MMRStrategy
    reasoning: str
    trajectory: list  # list[EmotionState] — the real, server-computed arc
    queries: list     # list[str] — exactly 4


def _build_result(parsed: dict) -> VentResult:
    """Validate the merged JSON and assemble a VentResult. Raises VentPipelineError."""
    try:
        current = EmotionState(
            valence=float(parsed["current_valence"]),
            arousal=float(parsed["current_arousal"]),
        )
        target = EmotionState(
            valence=float(parsed["target_valence"]),
            arousal=float(parsed["target_arousal"]),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise VentPipelineError(f"Missing or non-numeric valence/arousal: {e}. Got: {parsed}")

    try:
        strategy = MMRStrategy(parsed["strategy"])
    except (KeyError, ValueError):
        raise VentPipelineError(
            f"Unknown or missing strategy: {parsed.get('strategy')!r}. "
            f"Expected one of: {[s.value for s in MMRStrategy]}"
        )

    reasoning = parsed.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise VentPipelineError(f"Missing or empty reasoning. Got: {parsed}")

    queries = parsed.get("queries")
    if (
        not isinstance(queries, list)
        or len(queries) != 4
        or not all(isinstance(q, str) and q.strip() for q in queries)
    ):
        raise VentPipelineError(f"Expected exactly 4 non-empty queries, got: {queries!r}")

    # EmotionState already clamped VA to [-1, 1]; compute the real trajectory.
    trajectory = generate_trajectory(current, target, strategy, n_waypoints=4)
    return VentResult(
        current_emotion=current,
        target_emotion=target,
        strategy=strategy,
        reasoning=reasoning.strip(),
        trajectory=trajectory,
        queries=[q.strip() for q in queries],
    )


def run_vent(text: str, backend: LLMBackend) -> VentResult:
    """
    One LLM call → emotion + strategy + reasoning + 4 queries → VentResult.

    On a parse or validation failure the call is retried once; if the second
    attempt also fails, the error is raised. Backend transport errors propagate
    immediately (a retry won't fix a timeout or auth failure).
    """
    prompt = f"{MERGED_PROMPT_TEMPLATE}\n\nVENT: {text}"

    last_err = None
    for _ in range(2):  # initial attempt + one retry
        raw = backend.complete(prompt)
        try:
            return _build_result(extract_json(raw))
        except LLMError as e:  # unparseable JSON (extract_json) or failed validation
            last_err = e
    raise last_err
