"""
Tests for the shared JSON extraction (web/app/llm/base.py) and for
EmotionInference routing through an injected LLM backend.

We can't test a real `claude` subprocess or Anthropic API call in CI/sandbox, so
backend calls are exercised with a fake in-memory backend. The parser tests cover
the output formats a model produces in practice (clean JSON, fenced, preamble).
"""
import os
import sys

# Put the repo root (for `web`) and the pulse dir (for `venti_core`) on the path
# so the imports below work regardless of where the tests are invoked from.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PULSE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_REPO_ROOT, _PULSE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from web.app.llm.base import extract_json, get_backend, LLMError, LLMUnavailableError
from venti_core.inference import EmotionInference, InferenceError


class _FakeBackend:
    """Records prompts and returns a canned response — no real LLM call."""

    def __init__(self, response: str):
        self.response = response
        self.prompts: list[str] = []

    def complete(self, prompt: str, timeout: int = 60) -> str:
        self.prompts.append(prompt)
        return self.response


def test_clean_json():
    """Ideal case: model returns just JSON."""
    raw = '{"current_valence": -0.7, "current_arousal": 0.6, "target_valence": 0.2, "target_arousal": 0.1, "strategy": "discharge", "reasoning": "test"}'
    parsed = extract_json(raw)
    assert parsed["strategy"] == "discharge"
    assert parsed["current_valence"] == -0.7
    print("✅ clean JSON parses")


def test_json_with_markdown_fences():
    """Model sometimes wraps JSON in ```json ... ``` fences."""
    raw = """```json
{"current_valence": -0.5, "current_arousal": 0.4, "target_valence": 0.1, "target_arousal": 0.0, "strategy": "solace", "reasoning": "test"}
```"""
    parsed = extract_json(raw)
    assert parsed["strategy"] == "solace"
    print("✅ markdown-fenced JSON parses")


def test_json_with_plain_fences():
    """Plain ``` without language tag."""
    raw = """```
{"current_valence": 0.3, "current_arousal": 0.0, "target_valence": 0.5, "target_arousal": 0.2, "strategy": "entertainment", "reasoning": "test"}
```"""
    parsed = extract_json(raw)
    assert parsed["strategy"] == "entertainment"
    print("✅ plain-fenced JSON parses")


def test_json_with_preamble():
    """Model sometimes adds explanatory text before the JSON."""
    raw = """Here is my analysis:

{"current_valence": -0.6, "current_arousal": -0.3, "target_valence": 0.0, "target_arousal": 0.0, "strategy": "revival", "reasoning": "test"}

Hope that helps."""
    parsed = extract_json(raw)
    assert parsed["strategy"] == "revival"
    print("✅ JSON with preamble/postamble parses")


def test_unparseable_raises():
    """Total garbage should raise a clear error."""
    try:
        extract_json("hello world no json here")
        assert False, "should have raised"
    except LLMError as e:
        assert "Could not find JSON" in str(e)
        print("✅ unparseable input raises LLMError")


def test_inference_routes_through_backend():
    """EmotionInference should send the prompt to its backend and parse the reply."""
    backend = _FakeBackend(
        '{"current_valence": -0.7, "current_arousal": 0.6, "target_valence": 0.2, '
        '"target_arousal": 0.1, "strategy": "discharge", "reasoning": "frustrated"}'
    )
    inf = EmotionInference(backend=backend)
    result = inf.infer("third hour debugging this", context="backend work")

    assert result["strategy"].value == "discharge"
    assert result["current_emotion"].valence == -0.7
    assert result["target_emotion"].arousal == 0.1
    # The vent + context were actually formatted into the prompt sent to the backend.
    assert backend.prompts, "backend was never called"
    assert "third hour debugging this" in backend.prompts[0]
    assert "backend work" in backend.prompts[0]
    print("✅ EmotionInference routes through injected backend")


def test_inference_rejects_bad_strategy():
    """A parsed-but-invalid strategy is an InferenceError, not a silent pass."""
    backend = _FakeBackend(
        '{"current_valence": 0.0, "current_arousal": 0.0, "target_valence": 0.0, '
        '"target_arousal": 0.0, "strategy": "vibing", "reasoning": "x"}'
    )
    try:
        EmotionInference(backend=backend).infer("hi")
        assert False, "should have raised"
    except InferenceError as e:
        assert "Unknown strategy" in str(e)
        print("✅ EmotionInference rejects unknown strategy")


def test_get_backend_rejects_unknown():
    """An unrecognized LLM_BACKEND value fails fast (no backend import)."""
    prev = os.environ.get("LLM_BACKEND")
    os.environ["LLM_BACKEND"] = "banana"
    try:
        get_backend()
        assert False, "should have raised"
    except LLMUnavailableError:
        print("✅ get_backend rejects unknown LLM_BACKEND")
    finally:
        if prev is None:
            os.environ.pop("LLM_BACKEND", None)
        else:
            os.environ["LLM_BACKEND"] = prev


if __name__ == "__main__":
    test_clean_json()
    test_json_with_markdown_fences()
    test_json_with_plain_fences()
    test_json_with_preamble()
    test_unparseable_raises()
    test_inference_routes_through_backend()
    test_inference_rejects_bad_strategy()
    test_get_backend_rejects_unknown()
    print("\n🎉 All inference + backend tests passed.")
