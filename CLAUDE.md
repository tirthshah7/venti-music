# CLAUDE.md — Venti

Project context lives in `docs/venti-web-build-spec.md` (build spec, phases,
gates) and `README.md`. The rules below are standing constraints that apply
to every change, regardless of task.

## Standing rules

- All user-facing Spotify artifacts (playlists, descriptions) are private by
  default and never contain vent-derived text.
- Raw vent text never touches a log line, a cookie, or disk on the server
  (build rule 5); logs are event-shaped (`log.info("<event>", extra={...})`),
  never request bodies.
- Never open `.env`, `.spotify_cache`, or any file holding live tokens.
