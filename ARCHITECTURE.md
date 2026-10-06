# ResearchOS Phase 1 architecture

Electron hosts a React/TypeScript/Material UI application and supervises a Python 3.12 FastAPI sidecar. The sidecar binds only to loopback. An ephemeral session token authenticates all data requests. Renderer code has no Node access; a small context-isolated preload exposes file pickers and safe external links.

SQLAlchemy persists canonical Works, source identifiers and raw source hits, library metadata, files, annotations, materials and background jobs in SQLite. Alembic owns schema changes. FTS5 indexes local titles and notes. Files are copied into a SHA-256-addressed managed library; original user files are never modified.

OpenAlex and Crossref implement the same typed adapter contract. Canonicalization prioritizes normalized DOI, source IDs, then normalized title/first author/year; contradictory DOIs are never silently merged. Raw responses and field conflicts are retained. Search results are real API responses, never demo fallbacks. Partial source failures are visible.

PDF.js supplies selectable text and page rendering. Annotation rectangles use normalized page coordinates so zoom does not invalidate them. Materials snapshot bibliographic provenance and reference the canonical Work, managed PDF, page and annotation. Clicking a material restores that page and marker.

Long-running search/import jobs persist their input, state and result. Interrupted jobs are marked recoverable at startup; retry uses the stored request. Python API keys, if configured, are stored in the OS keyring, never the database or source tree.

Phase 2 extraction, Zotero and AI are intentionally not implemented. The supplied extraction schema is retained as a future contract.
