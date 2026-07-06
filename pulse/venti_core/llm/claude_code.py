"""
ClaudeCodeBackend — runs inference through the `claude` CLI in headless (`-p`)
mode. This keeps local development free on a Claude Max plan: auth is handled by
Claude Code's existing login, so no API key is needed.

Trade-offs vs the API backend:
- Pro: free under Max plan, no API key needed
- Pro: same model quality
- Con: slightly higher latency (subprocess startup ~1-2s)
- Con: requires the `claude` CLI installed and authenticated

The subprocess logic here was extracted verbatim from the old
venti_core/inference.py so behavior and error messages are unchanged.
"""
from __future__ import annotations

import shutil
import subprocess

from .base import LLMBackend, LLMError, LLMUnavailableError


class ClaudeCodeBackend(LLMBackend):
    """LLM transport backed by `claude -p`. No API key required."""

    def __init__(self, claude_binary: str | None = None):
        self.claude_binary = claude_binary or shutil.which("claude")
        if not self.claude_binary:
            raise LLMUnavailableError(
                "Could not find `claude` CLI on PATH. "
                "Install Claude Code from https://docs.claude.com/claude-code "
                "and run `claude login` first."
            )

    def complete(self, prompt: str, timeout: int = 60) -> str:
        # Run claude -p in headless mode. The prompt goes in via stdin to
        # avoid command-line length limits and shell escaping issues.
        try:
            result = subprocess.run(
                [self.claude_binary, "-p"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise LLMError(f"Claude Code timed out after {timeout} seconds.")
        except subprocess.CalledProcessError as e:
            raise LLMError(
                f"Claude Code exited with code {e.returncode}.\n"
                f"stderr: {e.stderr}\n"
                f"Run `claude login` if this is an auth issue."
            )

        return result.stdout.strip()
