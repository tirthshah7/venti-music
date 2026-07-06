"""
App-level Spotify client for the web layer: search-only, via the
client-credentials flow (no user context, no playback control).

Unlike venti_core.spotify_client.SpotifyClient (user OAuth + playback),
this client runs server-side for any visitor without a Spotify login.
Client-credentials tokens are app-level and short-lived (~1 hour), so
they are cached in memory only — never written to disk.

NOTE: For this app's client-credentials tokens, Spotify's /v1/search
omits `popularity` and `preview_url` from track objects (part of the
Nov 2024 API restrictions for newer apps). The popularity sort below
then degrades gracefully to Spotify's own relevance order, and
TrackInfo.preview_url is typically None. Verified live on 2026-07-06,
spotipy 2.26.0.
"""
import os
from typing import Optional

import spotipy
from pydantic import BaseModel
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyClientCredentials


class TrackInfo(BaseModel):
    id: str
    uri: str
    name: str
    artist: str
    album_art_url: Optional[str] = None
    preview_url: Optional[str] = None
    external_url: str


class AppSpotifyClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        auth = SpotifyClientCredentials(
            client_id=client_id or os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=client_secret or os.environ["SPOTIFY_CLIENT_SECRET"],
            cache_handler=MemoryCacheHandler(),
        )
        self.sp = spotipy.Spotify(auth_manager=auth)

    def find_tracks_for_queries(self, queries: list[str]) -> list[TrackInfo]:
        """
        One track per query (or fewer if a search returns nothing new):
        top-5 search results, most popular first, de-duped across queries.

        Uses the public sp.search(), unlike venti_core which calls
        sp._get() to dodge a suspected market=None bug. Verified on our
        pinned spotipy 2.26.0 that both paths return identical results
        (requests drops None-valued params before they hit the wire),
        so no workaround is needed here.
        """
        used_ids: set[str] = set()
        tracks: list[TrackInfo] = []
        for query in queries:
            track = self._find_track(query, exclude_track_ids=used_ids)
            if track:
                tracks.append(track)
                used_ids.add(track.id)
        return tracks

    def _find_track(
        self,
        query: str,
        exclude_track_ids: set[str],
    ) -> Optional[TrackInfo]:
        results = self.sp.search(q=query, type="track", limit=5, market="US")

        candidates = [
            t for t in results.get("tracks", {}).get("items", [])
            if t and t["id"] not in exclude_track_ids
        ]
        if not candidates:
            return None

        # `or 0` rather than a get() default: popularity is absent
        # entirely on this token type (see module docstring), and a
        # present-but-None value would break the sort comparison.
        candidates.sort(key=lambda t: t.get("popularity") or 0, reverse=True)
        return self._to_track_info(candidates[0])

    @staticmethod
    def _to_track_info(t: dict) -> TrackInfo:
        images = t.get("album", {}).get("images") or []
        return TrackInfo(
            id=t["id"],
            uri=t["uri"],
            name=t["name"],
            artist=", ".join(a["name"] for a in t.get("artists", [])),
            album_art_url=images[0]["url"] if images else None,
            preview_url=t.get("preview_url"),
            external_url=t.get("external_urls", {}).get("spotify", ""),
        )
