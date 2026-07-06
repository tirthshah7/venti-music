"""
LLM backend abstraction for Venti.

Two interchangeable transports implement `LLMBackend.complete()`:
  - ClaudeCodeBackend   — shells out to the `claude` CLI (free local dev on Max)
  - AnthropicAPIBackend — the official `anthropic` SDK (production / hosting)

`get_backend()` selects one from the LLM_BACKEND env var. Both backends raise the
same exception types (LLMUnavailableError / LLMError), so callers can't tell them
apart.

`extract_json()` is the shared, backend-agnostic JSON extractor used by
venti_core.inference and venti_core.query_generator to parse model output. It was
lifted verbatim from the (previously duplicated) inference-side implementation.
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """Raised when a backend fails to return usable output — a timeout, a
    transport failure, or a response we can't parse."""


class LLMUnavailableError(LLMError):
    """Raised when a backend cannot be initialized — e.g. the `claude` CLI is
    not on PATH, the `anthropic` package is missing, or no API key is set."""


class LLMBackend(ABC):
    """A transport that turns a prompt into raw model text."""

    @abstractmethod
    def complete(self, prompt: str, timeout: int = 60) -> str:
        """Send `prompt` to the model and return its raw text response."""
        raise NotImplementedError


def get_backend() -> LLMBackend:
    """Return the LLM backend selected by the LLM_BACKEND env var.

    "cli" → ClaudeCodeBackend, "api" → AnthropicAPIBackend. Defaults to "api".
    Backends are imported lazily so selecting one never forces the other's
    dependencies (e.g. the `anthropic` SDK) to be importable.
    """
    choice = os.environ.get("LLM_BACKEND", "api").strip().lower()
    if choice == "cli":
        from .claude_code import ClaudeCodeBackend
        return ClaudeCodeBackend()
    if choice == "api":
        from .anthropic_api import AnthropicAPIBackend
        return AnthropicAPIBackend()
    raise LLMUnavailableError(
        f"Unknown LLM_BACKEND: {choice!r}. Expected 'cli' or 'api'."
    )


def extract_json(raw: str) -> dict:
    """
    Robustly pull a JSON object out of a model response.

    Models usually return clean JSON when prompted, but sometimes wrap it in
    markdown fences or add preamble. We handle both cases: strip fences, try a
    direct parse, then fall back to scanning for the outermost {...} block.
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
        raise LLMError(
            f"Could not find JSON object in Claude Code response:\n{raw!r}"
        )

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise LLMError(
            f"Failed to parse JSON from Claude Code response: {e}\n"
            f"Raw output:\n{raw!r}"
        )
