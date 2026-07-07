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


def test_crisis_screen_copy_and_resources(source):
    # T5.1: acknowledgment first, then the resources — pinned here so a
    # frontend rewrite can't silently drop the one screen that must not break.
    for line in [
        "that sounds genuinely heavy — and it deserves more than a playlist.",
        "988 Suicide &amp; Crisis Lifeline",
        'href="tel:988"',
        "1-833-456-4566",
        "findahelpline.com",
    ]:
        assert line in source, f"missing crisis copy: {line!r}"
    # The crisis branch bails out before any music mechanics render.
    assert "data.crisis" in source
    assert 'setScreen("screen-crisis")' in source


def test_rating_available_without_saving(source):
    # T5.8: rating is per-session feedback, not a save reward — sessions
    # listened to via the embeds but never saved must still be ratable
    # (spec success criterion 2 needs ≥30 rated sessions). The block
    # lives OUTSIDE #saved-area, and every reveal re-arms it.
    saved_area = source.split('id="saved-area"')[1].split("</div>")[0]
    assert "rating" not in saved_area  # nothing rating-shaped inside
    assert '<div id="rating-block">' in source  # present, never hidden
    assert "resetRatingBlock" in source


def test_save_403_shows_message_and_never_redirects(source):
    # T5.5: 401 = re-authenticate (redirect to /api/auth/login); 403 =
    # Spotify said no at the app level — friendly line, no redirect. The
    # 403 branch must exist and must not contain the login redirect.
    assert "resp.status === 403" in source
    handler_403 = source.split("resp.status === 403", 1)[1].split("return;", 1)[0]
    assert "/api/auth/login" not in handler_403
    assert "window.location" not in handler_403


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
