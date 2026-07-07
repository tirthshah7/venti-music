# CLAUDE.md — Venti

Project context lives in `docs/venti-web-build-spec.md` (build spec, phases,
gates) and `README.md`. The rules below are standing constraints that apply
to every change, regardless of task.

## Standing rules

- All user-facing Spotify artifacts (playlists, descriptions) are private by
  default and never contain vent-derived text.
- Raw vent text never touches a log line, a cookie, or disk on the server
  (build rule 5); logs are event-shaped (`log.info("<event>", extra={...})`),
  never request bodies. The T5.10 SQLite event store is the one sanctioned
  datastore and holds event metadata only — its schema has no free-text
  columns, and nothing text-shaped may ever be passed to
  `store.record_event`.
- Never open `.env`, `.spotify_cache`, or any file holding live tokens.
