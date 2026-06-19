"""
Tests for the JSON extraction in inference.py.

We can't test the actual Claude Code subprocess call in CI/sandbox
(no claude binary), but we can test that the parser handles the various
output formats Claude Code produces in -p mode.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pulse.inference import EmotionInference, InferenceError


def test_clean_json():
    """Ideal case: Claude returns just JSON."""
    raw = '{"current_valence": -0.7, "current_arousal": 0.6, "target_valence": 0.2, "target_arousal": 0.1, "strategy": "discharge", "reasoning": "test"}'
    parsed = EmotionInference._extract_json(raw)
    assert parsed["strategy"] == "discharge"
    assert parsed["current_valence"] == -0.7
    print("✅ clean JSON parses")


def test_json_with_markdown_fences():
    """Claude sometimes wraps JSON in ```json ... ``` fences."""
    raw = """```json
{"current_valence": -0.5, "current_arousal": 0.4, "target_valence": 0.1, "target_arousal": 0.0, "strategy": "solace", "reasoning": "test"}
```"""
    parsed = EmotionInference._extract_json(raw)
    assert parsed["strategy"] == "solace"
    print("✅ markdown-fenced JSON parses")


def test_json_with_plain_fences():
    """Plain ``` without language tag."""
    raw = """```
{"current_valence": 0.3, "current_arousal": 0.0, "target_valence": 0.5, "target_arousal": 0.2, "strategy": "entertainment", "reasoning": "test"}
```"""
    parsed = EmotionInference._extract_json(raw)
    assert parsed["strategy"] == "entertainment"
    print("✅ plain-fenced JSON parses")


def test_json_with_preamble():
    """Claude sometimes adds explanatory text before the JSON."""
    raw = """Here is my analysis:

{"current_valence": -0.6, "current_arousal": -0.3, "target_valence": 0.0, "target_arousal": 0.0, "strategy": "revival", "reasoning": "test"}

Hope that helps."""
    parsed = EmotionInference._extract_json(raw)
    assert parsed["strategy"] == "revival"
    print("✅ JSON with preamble/postamble parses")


def test_unparseable_raises():
    """Total garbage should raise a clear error."""
    try:
        EmotionInference._extract_json("hello world no json here")
        assert False, "should have raised"
    except InferenceError as e:
        assert "Could not find JSON" in str(e)
        print("✅ unparseable input raises InferenceError")


if __name__ == "__main__":
    test_clean_json()
    test_json_with_markdown_fences()
    test_json_with_plain_fences()
    test_json_with_preamble()
    test_unparseable_raises()
    print("\n🎉 All inference parser tests passed.")
