# Changelog

## 0.1.0 — Phase 1 acceptance candidate

- Added real OpenAlex and Crossref adapters with typed queries, date filters, bounded retries and partial-source errors.
- Added canonical Work storage, raw source hits, field conflicts, SQLite FTS5 and Alembic migration.
- Added Library collections/tags/starred/status/notes and SHA-256-addressed PDF import.
- Added PDF.js text selection, persistent normalized highlights/notes and evidence/writing materials with page backlinks.
- Added durable jobs, interruption recovery, secure local session authentication and OS-keyring API keys.
- Added backend tests, frontend smoke tests, live-provider acceptance and PyInstaller/Electron Windows portable packaging.
- All 16 Phase 1 core acceptance criteria passed with documented verification boundaries, including user-confirmed Windows launch; no Phase 2 work.
