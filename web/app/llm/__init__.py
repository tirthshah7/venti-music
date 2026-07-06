"""Transport-agnostic LLM inference for Venti.

Public API re-exported for convenience:
    from web.app.llm import get_backend, extract_json, LLMBackend
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
