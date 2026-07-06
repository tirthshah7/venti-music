"""
Query generator: translates trajectory waypoints + strategy into natural-language
Spotify search queries, using a pluggable LLMBackend (see web/app/llm) as the
translator.

Background: Spotify deprecated the /recommendations endpoint and audio-features
in November 2024, so we can no longer ask "give me a song with valence=X,
energy=Y." Instead, we use the LLM to convert each waypoint into search terms
that approximate that emotional coordinate, and use Spotify's plain /search
endpoint (which is not deprecated and still works for new apps).
"""
from .models import EmotionState, MMRStrategy
from .llm.base import LLMBackend, extract_json, get_backend


QUERY_PROMPT_TEMPLATE = """You are a music search query generator.

Given an emotional trajectory (a sequence of valence-arousal coordinates)
and an MMR mood-regulation strategy, produce ONE short Spotify search query
per waypoint that will find a song matching that emotional point.

Waypoints are in valence-arousal space:
- valence: -1.0 (very negative) to +1.0 (very positive)
- arousal: -1.0 (very calm) to +1.0 (very intense/high energy)

Strategy: {strategy} ({strategy_description})

Trajectory waypoints:
{waypoints_text}

Search query rules:
- Each query should be 2-5 words, the kind of thing you'd type into Spotify search
- Combine genre/style + mood/feel terms (e.g. "aggressive metal", "melancholy indie folk", "ambient focus", "uplifting indie pop")
- For DISCHARGE strategy: lean into intensity — "rage metal", "punk anger", "hard rock catharsis"
- For SOLACE: warm, comforting — "sad indie acoustic", "melancholy folk", "lonely piano"
- For DIVERSION: orthogonal vibes — pick something stylistically unexpected
- For REVIVAL: gentle lift — "uplifting acoustic", "warm indie", "hopeful folk"
- For MENTAL_WORK: contemplative — "ambient post-rock", "atmospheric instrumental", "thoughtful indie"
- For ENTERTAINMENT: maintain mood — match current vibe
- For STRONG_SENSATION: peak emotional — "epic", "cinematic", "intense"

The trajectory should feel coherent — queries should flow naturally from one
to the next, gradually shifting alongside the VA arc. Do NOT use the same
query twice.

Output STRICT JSON, no markdown, no preamble:
{{
  "queries": ["query 1", "query 2", "query 3", "query 4"]
}}"""


STRATEGY_DESCRIPTIONS = {
    MMRStrategy.DISCHARGE: "cathartic release of negative emotion — let it OUT",
    MMRStrategy.SOLACE: "comfort, feel understood, not alone",
    MMRStrategy.REVIVAL: "gentle restoration of energy and positivity",
    MMRStrategy.DIVERSION: "orthogonal escape from the current emotional rut",
    MMRStrategy.MENTAL_WORK: "contemplate, process, reappraise",
    MMRStrategy.ENTERTAINMENT: "sustain an existing positive mood",
    MMRStrategy.STRONG_SENSATION: "seek peak emotional intensity",
}


class QueryGenerationError(RuntimeError):
    pass


class QueryGenerator:
    def __init__(self, backend: LLMBackend | None = None):
        self.backend = backend if backend is not None else get_backend()

    def generate_queries(
        self,
        trajectory: list[EmotionState],
        strategy: MMRStrategy,
    ) -> list[str]:
        """Returns one search query string per waypoint."""
        waypoints_text = "\n".join(
            f"  Waypoint {i+1}: valence={wp.valence:+.2f}, arousal={wp.arousal:+.2f}"
            for i, wp in enumerate(trajectory)
        )

        prompt = QUERY_PROMPT_TEMPLATE.format(
            strategy=strategy.value,
            strategy_description=STRATEGY_DESCRIPTIONS[strategy],
            waypoints_text=waypoints_text,
        )

        raw = self.backend.complete(prompt)
        parsed = extract_json(raw)

        queries = parsed.get("queries", [])
        if not isinstance(queries, list) or len(queries) != len(trajectory):
            raise QueryGenerationError(
                f"Expected {len(trajectory)} queries, got {len(queries)}: {queries}"
            )

        return queries
