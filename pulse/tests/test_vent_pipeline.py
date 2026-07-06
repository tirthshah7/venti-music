"""
Tests for the merged single-call vent pipeline (venti_core/llm/vent_pipeline.py).
The backend is mocked — no real LLM calls. Covers valid parse, VA clamping,
query-count + strategy-enum validation, retry-then-success, and retry-then-fail.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from venti_core.models import EmotionState, MMRStrategy
from venti_core.llm.base import LLMError
from venti_core.llm.vent_pipeline import (
    MERGED_PROMPT_TEMPLATE,
    run_vent,
    VentResult,
    VentPipelineError,
)


def _valid(**overrides) -> str:
    payload = {
        "current_valence": -0.7, "current_arousal": 0.6,
        "target_valence": 0.2, "target_arousal": 0.1,
        "strategy": "discharge",
        "reasoning": "High-arousal frustration; discharge first, then ease toward calm.",
        "queries": ["rage metal", "punk anger", "hard rock catharsis", "warm indie"],
    }
    payload.update(overrides)
    return json.dumps(payload)


class _FixedBackend:
    """Returns the same response every call; records prompts."""

    def __init__(self, response: str):
        self.response = response
        self.prompts: list[str] = []

    @property
    def calls(self) -> int:
        return len(self.prompts)

    def complete(self, prompt: str, timeout: int = 60) -> str:
        self.prompts.append(prompt)
        return self.response


class _ScriptedBackend:
    """Returns queued responses in order (clamping to the last)."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts: list[str] = []

    @property
    def calls(self) -> int:
        return len(self.prompts)

    def complete(self, prompt: str, timeout: int = 60) -> str:
        self.prompts.append(prompt)
        return self.responses[min(self.calls - 1, len(self.responses) - 1)]


def test_valid_parse():
    b = _FixedBackend(_valid())
    r = run_vent("third hour debugging this kafka thing", b)
    assert isinstance(r, VentResult)
    assert r.strategy is MMRStrategy.DISCHARGE
    assert r.current_emotion.valence == -0.7
    assert r.target_emotion.arousal == 0.1
    assert r.queries == ["rage metal", "punk anger", "hard rock catharsis", "warm indie"]
    assert len(r.trajectory) == 4 and all(isinstance(w, EmotionState) for w in r.trajectory)
    assert b.calls == 1
    assert "third hour debugging this kafka thing" in b.prompts[0]
    print("✅ valid merged JSON parses into a VentResult")


def test_va_clamped_via_emotionstate():
    b = _FixedBackend(_valid(current_valence=2.0, target_arousal=-3.0))
    r = run_vent("x", b)
    assert r.current_emotion.valence == 1.0   # clamped from 2.0
    assert r.target_emotion.arousal == -1.0   # clamped from -3.0
    print("✅ out-of-range valence/arousal clamped via EmotionState")


def test_wrong_query_count_raises():
    b = _FixedBackend(_valid(queries=["only", "three", "here"]))
    try:
        run_vent("x", b)
        assert False, "should have raised"
    except VentPipelineError as e:
        assert "4" in str(e)
    assert b.calls == 2  # initial attempt + one retry
    print("✅ wrong query count raises after one retry")


def test_strategy_enum_validation():
    b = _FixedBackend(_valid(strategy="vibing"))
    try:
        run_vent("x", b)
        assert False, "should have raised"
    except VentPipelineError as e:
        assert "strategy" in str(e).lower()
    assert b.calls == 2
    print("✅ invalid strategy rejected after one retry")


def test_retry_then_success():
    b = _ScriptedBackend(["not json at all", _valid()])
    r = run_vent("x", b)
    assert r.strategy is MMRStrategy.DISCHARGE
    assert b.calls == 2  # first response bad, recovered on the retry
    print("✅ recovers on the retry when the first response is bad")


def test_retry_then_fail():
    b = _FixedBackend("this is not json")
    try:
        run_vent("x", b)
        assert False, "should have raised"
    except LLMError:  # extract_json raises LLMError; VentPipelineError subclasses it
        pass
    assert b.calls == 2  # exactly one retry, then raise
    print("✅ retry-then-fail raises after exactly two attempts")


def test_merged_prompt_has_second_person_voice_instruction():
    # T4.3: the reasoning line is shown to the person as the reveal
    # headline — it must speak to them, not about them.
    assert "spoken directly to the person as 'you' (second person)" in MERGED_PROMPT_TEMPLATE
    assert "never 'the user', never third person" in MERGED_PROMPT_TEMPLATE
    print("✅ merged prompt instructs second-person reasoning voice")


def test_voice_instruction_lives_in_bridge_text_not_sliced_rules():
    # The sliced blocks must remain verbatim substrings of their source
    # templates — additions like T4.3 belong to the bridge text only.
    from venti_core.inference import INFERENCE_PROMPT_TEMPLATE
    from venti_core.query_generator import QUERY_PROMPT_TEMPLATE
    from venti_core.llm import vent_pipeline as vp

    assert vp._PSYCH_RULES in INFERENCE_PROMPT_TEMPLATE
    assert vp._QUERY_RULES in QUERY_PROMPT_TEMPLATE
    assert "never 'the user'" not in vp._PSYCH_RULES
    assert "never 'the user'" not in vp._QUERY_RULES
    print("✅ sliced rule blocks untouched; voice instruction is bridge-only")


if __name__ == "__main__":
    test_valid_parse()
    test_va_clamped_via_emotionstate()
    test_wrong_query_count_raises()
    test_strategy_enum_validation()
    test_retry_then_success()
    test_retry_then_fail()
    test_merged_prompt_has_second_person_voice_instruction()
    test_voice_instruction_lives_in_bridge_text_not_sliced_rules()
    print("\n🎉 All vent pipeline tests passed.")
