"""
Query generator: translates trajectory waypoints + strategy into natural-language
Spotify search queries, using Claude Code as the translator.

Background: Spotify deprecated the /recommendations endpoint and audio-features
in November 2024, so we can no longer ask "give me a song with valence=X,
energy=Y." Instead, we use the LLM to convert each waypoint into search terms
that approximate that emotional coordinate, and use Spotify's plain /search
endpoint (which is not deprecated and still works for new apps).
"""
import json
import shutil
import subprocess

from .models import EmotionState, MMRStrategy


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
    def __init__(self, claude_binary: str | None = None):
        self.claude_binary = claude_binary or shutil.which("claude")
        if not self.claude_binary:
            raise QueryGenerationError(
                "Could not find `claude` CLI on PATH. "
                "Install Claude Code and run `claude login` first."
            )

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
            raise QueryGenerationError("Claude Code timed out after 60 seconds.")
        except subprocess.CalledProcessError as e:
            raise QueryGenerationError(
                f"Claude Code exited with code {e.returncode}.\nstderr: {e.stderr}"
            )

        raw = result.stdout.strip()
        parsed = self._extract_json(raw)

        queries = parsed.get("queries", [])
        if not isinstance(queries, list) or len(queries) != len(trajectory):
            raise QueryGenerationError(
                f"Expected {len(trajectory)} queries, got {len(queries)}: {queries}"
            )

        return queries

    @staticmethod
    def _extract_json(raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise QueryGenerationError(f"No JSON found in: {raw!r}")
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as e:
            raise QueryGenerationError(f"Bad JSON: {e}\nRaw: {raw!r}")
