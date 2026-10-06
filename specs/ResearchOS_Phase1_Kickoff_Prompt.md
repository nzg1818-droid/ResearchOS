# ResearchOS — Phase 1 Kickoff Prompt for Codex

You are implementing Phase 1 of ResearchOS, a local-first Windows literature research workstation.

## Source specifications
Use these project specifications as authoritative:
1. `ResearchOS_Codex_Master_Prompt.md`
2. `ResearchOS_Architecture_Overview.md`
3. `electrocatalysis_extraction_schema.json`

Do not implement later phases unless required to keep architecture extensible.

## Phase 1 objective
Deliver a genuinely usable vertical slice:

Search literature
→ merge/deduplicate
→ save to local Library
→ open DOI/publisher
→ locate lawful OA copy
→ import/attach local PDF
→ read PDF
→ highlight/annotate
→ save material/evidence
→ click saved material and jump back to original PDF page

## Required stack
Frontend/Desktop:
- Electron
- React + TypeScript + Vite
- Material UI
- PDF.js

Backend:
- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy/SQLModel
- SQLite + FTS5
- Alembic
- httpx + tenacity
- PyMuPDF
- watchdog where useful
- pytest

## Required Phase 1 features

### 1. Project/repository foundation
Create a Git repository named `ResearchOS` unless the user specifies another name.
Prefer a private repository.
Create:
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `DEV_SETUP.md`
- `USER_GUIDE.md`
- `CHANGELOG.md`
- `.env.example`
- `.gitignore`
- backend/frontend folders
- Alembic migrations
- mock/demo data
- test folders

### 2. Search
Implement real API-backed search adapters for:
- OpenAlex
- Crossref

Search modes:
- keyword
- exact title
- author
- DOI
- publication date range

Result fields:
- title
- authors
- journal/source
- publication date/year
- DOI
- citation count when available
- OA status/location when available
- source provenance

No fake/demo results in production paths.

### 3. Deduplication
Canonical priority:
1. normalized DOI
2. source identifiers
3. normalized title + first author + year
4. PDF SHA-256

The same paper returned by OpenAlex and Crossref must appear as one Work.

### 4. Local Library
Implement:
- add/remove work from library
- collections
- tags
- starred
- reading status
- notes
- attachments metadata
- persistent SQLite storage

### 5. Full-text workflow
Implement:
- Open DOI
- Open publisher
- Find lawful OA copy
- Attach local PDF
- automatic PDF hash
- DOI/title extraction when possible
- match attached PDF to existing Work
- avoid duplicate file imports

Do not implement paywall bypass or institutional password automation.

### 6. PDF Reader
Implement PDF.js reader with:
- page navigation
- text selection
- highlight
- comment/note
- persistent annotations
- "Save as evidence"
- "Save as writing material"

### 7. Knowledge/Material Bank
Every saved material must retain:
- work ID
- paper title
- DOI if known
- authors/year
- PDF file reference
- page number
- selected text
- surrounding context where feasible
- annotation coordinates where feasible
- note
- tags
- timestamp

Clicking a saved material must reopen the PDF at the correct page and highlight/locate the source.

### 8. Task/error handling
Provide:
- background task status for search/import
- clear errors
- retry for transient API failures
- API rate-limit handling
- logs useful for debugging

## Phase 1 mandatory acceptance tests

Do not declare Phase 1 complete until all pass:

1. Search `NiFe LDH alkaline water electrolysis` across a date range using both OpenAlex and Crossref.
2. Merge results without duplicate DOI records.
3. Search by exact DOI.
4. Search by exact title.
5. Search by author.
6. Open DOI/publisher link from a result.
7. Discover a lawful OA PDF where available.
8. Import a manually downloaded PDF and attach it to the correct existing Work.
9. Re-import the same PDF and confirm no duplicate attachment is created.
10. Import a folder containing multiple PDFs without crashing.
11. Highlight a sentence in a PDF, add a note, restart the app, and confirm persistence.
12. Open Knowledge/Material Bank, click the saved highlight, and jump back to the exact paper/page.
13. Verify database persistence after app restart.
14. Backend unit tests pass.
15. Frontend smoke tests pass.
16. Build/package a Windows runnable app or installer successfully.

## Quality gate
Phase 1 is NOT complete if:
- core search results are mocked
- OpenAlex/Crossref adapters are not real
- duplicate papers remain as separate Works
- annotations disappear after restart
- source backlink from material to PDF does not work
- app cannot be built on Windows
- credentials are stored in plaintext

## Git/GitHub workflow
- Commit in logical increments.
- Push all work to GitHub.
- Prefer feature branches and a final Phase 1 pull request.
- Include a final `PHASE1_REPORT.md` containing:
  - implemented features
  - architecture decisions
  - exact tests executed and results
  - known limitations
  - screenshots or UI notes
  - Windows launch/build commands
  - commit SHA
  - any feature that is incomplete

## Final response to user
When finished, do not merely say "done".
Return:
1. GitHub repository URL/name
2. branch/PR
3. latest commit SHA
4. test summary
5. Windows run/build instructions
6. known limitations
7. explicit statement of which acceptance tests passed/failed

Start now. Implement working code, run tests, fix failures, and push the finished Phase 1 to GitHub.
