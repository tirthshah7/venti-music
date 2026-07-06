"""
T4.1 grep-level checks on the single-file frontend: the copy lines that
carry the product's honesty live in tests so a rewrite can't silently
drop them, and the dead-end paths (preview_url player, third-party
scripts, localStorage) stay dead.
"""
from pathlib import Path

import pytest

INDEX = Path(__file__).resolve().parents[1] / "static" / "index.html"


@pytest.fixture(scope="module")
def source():
    return INDEX.read_text()


def test_spec_copy_present(source):
    for line in [
        "Tell it like it is. Get music that actually helps.",
        "what's going on?",
        ">vent</button>",
        "you've vented a lot this hour — give it a minute",
        # This line is only allowed in the UI because it is true (the
        # privacy tests in test_routers.py are what keep it true).
        "something broke on our end. your words weren't stored.",
        "did the music move you?",
        "noted. come back whenever.",
        "vent again",
        "connect spotify",
        "open your playlist",
    ]:
        assert line in source, f"missing spec copy: {line!r}"


def test_uses_spotify_embeds_lazily(source):
    assert "open.spotify.com/embed/track/" in source
    assert 'loading = "lazy"' in source or 'loading="lazy"' in source


def test_no_preview_url_player(source):
    # preview_url is dead (always null) on client-credentials tokens —
    # spec amendment 2d86971 replaced the player with embeds.
    assert "preview_url" not in source
    assert "<audio" not in source
    assert "new Audio" not in source


def test_no_third_party_scripts_or_trackers(source):
    assert "<script src" not in source
    assert "googleapis" not in source
    assert "analytics" not in source
    assert "localStorage" not in source  # sessionStorage only, result only


def test_char_counter_and_cap(source):
    assert 'maxlength="1000"' in source
    assert "800" in source  # counter appears only past 800
