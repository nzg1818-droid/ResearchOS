# ResearchOS Phase 1 report

Date: 2026-10-06. Repository: https://github.com/nzg1818-droid/ResearchOS

Branch: `feat/phase1`. Tested implementation commit: `cbe2d9d84222c243ca953793f78e18a88ee83cac` (the following documentation commit adds this report and CI, without changing application code). Run `git rev-parse HEAD` for the final checkout SHA; the delivery response also records it.

## Outcome

All 16 kickoff core acceptance criteria passed using the evidence and verification boundaries below. Phase 1 is delivered as a Windows x64 portable runnable application. **Phase 2 was not started.**

The app provides real dual-provider search → canonical deduplication → Library → lawful external links/OA discovery → local PDF import → PDF.js reading/text selection → persistent highlights and notes → evidence/writing materials → original PDF/page/coordinate backlink.

## Acceptance matrix

| # | Core requirement | Result | Evidence |
|---|---|---|---|
| 1 | NiFe LDH query across a date range, both providers | PASS | Live request `NiFe LDH alkaline water electrolysis`, 2020-01-01 through 2026-10-06: OpenAlex 20, Crossref 20, no provider errors. |
| 2 | No duplicate DOI records | PASS | 40 source hits merged to 31 canonical Works. DOI uniqueness asserted. Unit tests also cover normalization, metadata fallback, conflicting DOIs and a later DOI bridge preserving files/notes. |
| 3 | Exact DOI | PASS | `10.1016/j.inoche.2025.115189`: one hit from each provider, one canonical Work. |
| 4 | Exact title | PASS | `ZrO2 embedded in NiFe-LDH/PVA network as the membrane of alkaline water electrolysis`: one exact normalized-title hit from each provider, one Work. |
| 5 | Author | PASS | `Qian Lu`: 10 hits from each provider; real OpenAlex author-ID resolution and Crossref author query. |
| 6 | DOI/publisher link | PASS | Clicked Open DOI on a real search result; a browser tab opened `https://doi.org/10.1038/s41467-024-54754-5`. Publisher links use the same restricted HTTP(S) opener. |
| 7 | Lawful OA PDF discovery | PASS | OpenAlex returned a licensed PubMed Central PDF location for `Corrosion-resistant NiFe anode towards kilowatt-scale alkaline seawater electrolysis`, DOI `10.1038/s41467-024-54754-5`. Discovery is distinct from remote-host availability. |
| 8 | Attach a locally downloaded PDF to an existing Work | PASS | Downloaded the actual `Attention Is All You Need` PDF from arXiv, imported it from local disk into the existing title/author-matched Work. Independent test verifies automatic extracted-DOI matching. |
| 9 | Re-import without duplicate attachment | PASS | Real PDF re-import returned existing `file_id=1`, `work_id=52`, `duplicate=true`; unit test checks row count and rejects cross-Work duplicate attachment. |
| 10 | Import a folder of PDFs without crashing | PASS | 100 distinct generated PDFs plus one deliberately broken PDF: 100 imports succeeded; the bad file was isolated. Retry deduplicated all 100. |
| 11 | Highlight, note, restart and persistence | PASS | In the real PDF.js UI, selected page-2 text, entered a note/tags and saved evidence. Stopped/restarted the frozen backend process and reloaded the UI: text, rectangles and note persisted. |
| 12 | Material-bank backlink to correct PDF/page | PASS | After restart, clicked Knowledge → Open source · page 2. Same PDF reopened at page 2 with focused highlight and saved note. Frontend regression verifies file/page/annotation routing. |
| 13 | Database persistence after restart | PASS | Real process restart plus unit test constructing a new app instance over the same database retained library metadata, collections, PDF, annotations and material provenance. |
| 14 | Backend tests | PASS | `python -m pytest -q -p no:cacheprovider`: **11 passed**. |
| 15 | Frontend smoke tests | PASS | Vitest: **3 passed**. TypeScript `--noEmit` and Vite production build also passed. |
| 16 | Windows runnable build | PASS | PyInstaller + official Electron portable packaging passed. User extracted the ZIP into an ordinary directory and explicitly confirmed `ResearchOS.exe` opens normally. |

Machine-readable evidence: [live API results](docs/live-acceptance.json), [UI and restart notes](docs/ui-acceptance.json).

Verification boundaries: native Windows file-picker interaction was not automated in the restricted Codex workspace. Its authenticated import path was tested with local files, while the complete reading/highlight/backlink workflow was exercised in the same React renderer against the frozen Windows sidecar. Windows desktop launch was separately confirmed by the user. This is not a claim that every UI action was automated inside the packaged Electron window.

## Exact commands executed

From `backend/` (Python executable was `../.venv/Scripts/python.exe`):

```powershell
../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
$env:PYTHONPATH="$PWD"
../.venv/Scripts/python.exe tests/live_acceptance.py
```

From the repository root:

```powershell
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vitest/vitest.mjs run --pool=threads --configLoader native
node node_modules/vite/bin/vite.js build --configLoader native
./scripts/build-windows.ps1
```

The build script executes PyInstaller with `--collect-all keyring --collect-all pymupdf --add-data 'alembic.ini;.' --add-data 'migrations;migrations'`, then `scripts/package_portable.py`.

Production npm audit: **0 reported vulnerabilities**. Full build/dev dependency tree: 8 moderate advisories at verification time; no high/critical advisories. The full tree is not shipped in the portable application. Pytest emits one upstream Starlette/httpx deprecation warning; all assertions pass. Vite warns about a large PDF-enabled renderer bundle; build succeeds.

## Windows deliverable

- `release/ResearchOS-0.1.0-win-x64.zip` (204,265,103 bytes)
- SHA-256: `fcf675bee9e3d8a24f17367c7b4a4aa7f806baeb1e025ff4f8988b7a8b50808e`
- Extract the entire ZIP and run `ResearchOS-portable/ResearchOS.exe`.
- Target computer does not need Python or Node.
- Rebuild: `powershell -File scripts/build-windows.ps1` after following `DEV_SETUP.md`.
- Installer configuration is supplied, but the NSIS installer was **not** validated. The acceptance criterion permits a runnable app or installer; the portable runnable app is the validated deliverable.

The initial managed workspace ACL prevented Electron's sandbox from reading its installation directory. The session could not change that ACL. No sandbox was disabled; extracting into a normal directory resolved launch according to the user's test. The final package was rebuilt after regression fixes using the same launcher/packaging path.

## Architecture decisions

- One canonical Work, database-unique normalized DOI, durable source identifiers/hits and field conflict tracking. Later DOI bridges preserve user data and file/annotation backlinks.
- Phase 1 bibliographic authors/tags and provenance are typed/JSON snapshots; later-phase extraction/Zotero tables are deliberately not introduced. Relational foreign keys link Works, files, annotations, materials and collections.
- Alembic owns initial schema; SQLite WAL/FTS5 supports local persistence/search. All modifying operations are serialized within the sidecar.
- PDFs are copied to content-addressed managed storage. Original files are never modified. Broken files do not abort a folder batch.
- Electron uses context isolation, a sandboxed renderer, a narrow preload and loopback-only backend with per-launch random authentication. API keys live in OS keyring.
- Annotation rectangles are normalized to page dimensions. Materials include selected text, page context, notes, tags, timestamp, bibliographic snapshot and PDF hash/reference.
- Search/import requests and states persist. Interrupted work can be retried; already imported hashes remain idempotent.

## UI notes

Six implemented destinations: Search, Library, Reader, Knowledge, Tasks and Settings. Search shows source chips, metadata, OA status and direct actions. Library provides collections, FTS search, status/tags/notes and attachments. Reader shows PDF/page controls alongside evidence notes; Knowledge cards reopen the original source. Tasks exposes source errors and batch-file failures. Settings shows local storage and secure optional API-key entry.

## Known limitations / incomplete optional features

- Unsigned portable build; no tested installer, code signing, updater or automated full native-window test suite.
- Search currently requests up to 100 results per source (UI defaults to 20); no cursor pagination or comprehensive systematic-review coverage claim.
- Provider metadata may describe a different edition or contain errors. Exact-title/author matching cannot establish scientific identity by itself; raw provenance/conflicts remain available in storage.
- OA discovery does not bypass remote host login, access challenges or paywalls. Some discovered OA hosts returned HTML rather than a PDF during verification; a lawful arXiv PDF was used to test the import/reader path.
- Scanned/image-only PDFs need an existing text layer for selection; OCR is not included. Metadata extraction is heuristic, and users can explicitly choose a Work when attaching a PDF.
- Phase 1 supports text highlights; figure/table drawing, annotation editing, nested collections, watcher automation, advanced cancellation/progress and export are not part of this delivery.
- GitHub repository was supplied/created during the session as **public**; its visibility was not changed. No test PDFs, personal library database, tokens or API keys are committed.
- Phase 2/3/4 capabilities remain absent.
