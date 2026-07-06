"""
AnthropicAPIBackend — runs inference through the official `anthropic` SDK.

This is the production / hosting transport: it needs an ANTHROPIC_API_KEY and
bills against API credits (not a Max plan). SDK timeouts and errors are mapped
onto the same exception types the CLI backend raises (LLMError /
LLMUnavailableError) so callers can't tell the two backends apart.

`anthropic` is imported lazily inside __init__, so importing this module never
requires the SDK to be installed — only constructing the backend does.
"""
from __future__ import annotations

import os

from .base import LLMBackend, LLMError, LLMUnavailableError

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024


class AnthropicAPIBackend(LLMBackend):
    """LLM transport backed by the Anthropic Messages API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        try:
            import anthropic
        except ImportError as e:
            raise LLMUnavailableError(
                "The `anthropic` package is not installed. "
                "Install it with `pip install anthropic` (see web/requirements.txt)."
            ) from e

        self._anthropic = anthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMUnavailableError(
                "ANTHROPIC_API_KEY is not set. Export it or add it to your .env."
            )
        self.model = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        self.client = anthropic.Anthropic(api_key=key)

    def complete(self, prompt: str, timeout: int = 60) -> str:
        try:
            # Sampling params (temperature / top_p / top_k) are intentionally NOT
            # set: the Claude 4.x models — including claude-sonnet-4-6 — reject them
            # with a 400 ("temperature is deprecated for this model"). Determinism
            # and reasoning depth are governed by the model + effort, not a
            # temperature knob, so there is nothing to tune here.
            message = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout,
            )
        except self._anthropic.APITimeoutError as e:
            raise LLMError(
                f"Anthropic API request timed out after {timeout} seconds."
            ) from e
        except self._anthropic.APIError as e:
            raise LLMError(f"Anthropic API call failed: {e}") from e

        # Concatenate the text blocks of the response into one string.
        parts = [
            block.text
            for block in message.content
            if getattr(block, "type", None) == "text"
        ]
        return "".join(parts).strip()
