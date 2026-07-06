"""Transport-agnostic LLM inference for Venti.

Lives inside the engine so venti_core has no dependency on the web layer.
Public API:
    from venti_core.llm import get_backend, extract_json, LLMBackend
"""
from .base import (
    LLMBackend,
    LLMError,
    LLMUnavailableError,
    extract_json,
    get_backend,
)

__all__ = [
    "LLMBackend",
    "LLMError",
    "LLMUnavailableError",
    "extract_json",
    "get_backend",
]
