"""
Tests for QueryGenerator routing through an injected LLM backend and its
query-count validation. No real LLM call — a fake backend returns canned JSON.
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PULSE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_REPO_ROOT, _PULSE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from venti_core.models import EmotionState, MMRStrategy
from venti_core.query_generator import QueryGenerator, QueryGenerationError


class _FakeBackend:
    """Records prompts and returns a canned response — no real LLM call."""

    def __init__(self, response: str):
        self.response = response
        self.prompts: list[str] = []

    def complete(self, prompt: str, timeout: int = 60) -> str:
        self.prompts.append(prompt)
        return self.response


def _trajectory(n: int = 4) -> list[EmotionState]:
    return [EmotionState(valence=-0.5 + 0.2 * i, arousal=0.4 - 0.1 * i) for i in range(n)]


def test_query_generator_routes_through_backend():
    """generate_queries sends the strategy/waypoints prompt to the backend and
    returns the parsed queries."""
    backend = _FakeBackend('{"queries": ["rage metal", "punk anger", "hard rock", "warm indie"]}')
    qg = QueryGenerator(backend=backend)
    queries = qg.generate_queries(_trajectory(4), MMRStrategy.DISCHARGE)

    assert queries == ["rage metal", "punk anger", "hard rock", "warm indie"]
    assert backend.prompts, "backend was never called"
    assert "discharge" in backend.prompts[0]
    print("✅ QueryGenerator routes through injected backend")


def test_query_count_mismatch_raises():
    """Wrong number of queries for the trajectory is a QueryGenerationError."""
    backend = _FakeBackend('{"queries": ["only one"]}')
    try:
        QueryGenerator(backend=backend).generate_queries(_trajectory(4), MMRStrategy.SOLACE)
        assert False, "should have raised"
    except QueryGenerationError as e:
        assert "Expected 4 queries" in str(e)
        print("✅ QueryGenerator rejects wrong query count")


if __name__ == "__main__":
    test_query_generator_routes_through_backend()
    test_query_count_mismatch_raises()
    print("\n🎉 All query generator tests passed.")
