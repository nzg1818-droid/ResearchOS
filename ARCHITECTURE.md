# ResearchOS architecture — Phase 2B1

Electron hosts a React/TypeScript/MUI renderer and supervises a Python FastAPI sidecar bound to loopback. An ephemeral session token authenticates requests. Context isolation, managed SHA-256 PDF copies, normalized annotation rectangles and source-centered Knowledge backlinks remain intact.

SQLAlchemy/Alembic owns SQLite changes. Phase 1 schema is frozen; 0002 introduces portable file paths, indexed identity/provenance and Zotero state. Migration 0003 adds documents/pages/blocks/chunks, FTS5, provider configuration, AI/extraction runs, evidence anchors, immutable verification decisions and paper questions/answers. Before upgrading 0001 or 0002, SQLite backup creates a recoverable snapshot. Backups include the entire SQLite snapshot and managed PDFs, accept schemas 0002/0003, and exclude OS credential-store secrets. Downgrade requires restoring the pre-migration backup into a new folder.

`app/intelligence/parsing.py` runs PyMuPDF in a worker thread. Every page and ordered text block retains source geometry. Conservative headings and caption candidates are stored; text chunks are bounded at 1800 characters with stable IDs for the same parsed document. Scanned pages produce Needs OCR. No OCR or vision model is used. Existing source-hit abstracts provide fallback; unknown fields stay null.

`providers.py` defines LLMProvider, configurable HTTPS OpenAI-compatible chat-completions, loopback Ollama, and deterministic Mock adapters. Keys live only in OS keyring. Endpoint changes clear an old key before reuse. Redirects are not followed. Provider errors are sanitized and unsolicited reasoning fields are ignored. The Ollama request format follows https://docs.ollama.com/api/chat .

`service.py` selects relevant chunks using paper-scoped FTS, sends targeted extraction sections using versioned prompts/schema, validates strict Pydantic output and source anchors, and records provider/model/schema/prompt/source provenance. Cache keys include Work, source bytes, parser/text hashes, schema/prompt versions, provider endpoint/type/model, level and relevant generation settings. Successful results reuse cache by default. Human corrections append decisions without changing the extraction payload. No app-computed conversion action is exposed.

Cloud calls require explicit paper/batch consent at API and UI boundaries. Consent is held for that execution only and is not persisted as a reusable permission. Imported PDFs never trigger AI. Audit metadata may record that consent was given for a past run. Resume requires renewed cloud consent. No web retrieval or cross-paper aggregation is part of Ask Paper.

`api.py` persists batch tasks through the existing Job model, with per-paper states and bounded workers (1–8). A failing paper does not abort others. Pause/cancel stop starting new papers; current requests finish safely. Resume skips successful papers and cached extraction prevents duplicate work. Crash recovery marks jobs interrupted; the user explicitly resumes. Retained result maps scale with selected IDs, bounded at 1000 and requiring confirmation above 50.

Reader, Intelligence and AI settings are separate lazy chunks. Source buttons preserve the open Intelligence panel, route to the cited file/page and use normalized bbox overlays for zoom/rotation. Verification and Ask Paper claims can enter Knowledge with source anchors. JSON/CSV exports include provenance and review status, never provider keys. Metadata/abstract results are explicitly distinguished from full-text/verified results.

Phase 2B2/3 features remain excluded: no ranking, cross-paper synthesis, vector DB, Watch, citation analytics, OCR or automatic figure/table interpretation.
