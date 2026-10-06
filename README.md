# ResearchOS

A local-first Windows literature research workstation. Phase 1 connects real OpenAlex/Crossref search to a canonical local library, managed PDFs, persistent highlights and a source-linked material bank.

**Status:** Phase 1 core acceptance passed (11 backend tests, 3 frontend smoke tests, live API and source-backlink verification, user-confirmed Windows launch). Phase 2 has not started. See [PHASE1_REPORT.md](PHASE1_REPORT.md) for evidence and verification boundaries.

## Run on Windows

Download/extract the Windows portable ZIP, then run `ResearchOS-portable/ResearchOS.exe`. Keep the entire folder together. Python and Node are bundled/not required on the target computer. This is an unsigned build.

For source setup, testing and packaging, see [DEV_SETUP.md](DEV_SETUP.md). For workflows and local data backup, see [USER_GUIDE.md](USER_GUIDE.md).

## Stack

Electron, React, TypeScript, Vite, Material UI, PDF.js; Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, SQLite/FTS5, Alembic, httpx/tenacity and PyMuPDF. API keys use the operating-system keyring.

Production searches never fall back to demo data. This application does not bypass paywalls, automate institutional passwords or modify Zotero databases.
