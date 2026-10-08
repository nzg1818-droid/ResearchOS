# ResearchOS v0.2 / Phase 2A Product Specification

## Product intent
Phase 2A turns the Phase 1 literature workstation into a reliable personal research hub that can safely interoperate with Zotero while remaining local-first and portable.

Target flow:

Search / PDF Import
→ Canonical Work
→ ResearchOS Library
↕
Zotero
→ Collections / tags / notes / attachments
→ Conflict-safe synchronization
→ Backup / restore / migration

This phase also implements the reader-first UI redesign in `specs/UI_V2_SPEC.md`.

## 1. Preconditions
- Phase 1 PR #1 is merged to `main`.
- Phase 2A branch: `feat/phase2a-zotero`.
- All Phase 1 tests must pass before implementation.
- Preserve all Phase 1 behavior and user data.
- Do not edit Zotero's SQLite database directly.

## 2. Data/storage hardening

### 2.1 Portable managed attachment paths
Phase 1 stores managed attachment paths as absolute paths. Replace this with portable storage semantics.

Required:
- Store ResearchOS-managed attachment paths relative to the configured ResearchOS data root.
- Resolve paths through one storage service/helper, not ad hoc string joins across the codebase.
- Existing Phase 1 DBs migrate safely.
- Before schema-changing migration, automatically create a DB backup.
- Copying the ResearchOS data folder to another absolute location must preserve attachments and source backlinks.
- Original user files must never be modified.

### 2.2 Search provenance
Add normalized search provenance, at minimum:
- `search_runs`
- `search_run_hits` or equivalent relationship
- request query, mode, date filters, source list, timestamps, result counts/errors
- mapping from provider result to canonical Work

Preserve raw source metadata while preventing uncontrolled duplicate provenance growth.

### 2.3 Scalable matching
Remove corpus-wide O(N) title scans during PDF matching.

Matching order:
1. DOI
2. stable source identifiers
3. indexed normalized title key + author/year candidates
4. explicit/manual fallback

Add a performance regression test against >=10,000 synthetic Works.

### 2.4 Better annotation context
For new annotations store a bounded local context window around the selected text rather than a large page prefix.

Preserve:
- selected text
- preceding/following context
- page
- normalized coordinates
- note
- tags
- timestamp
- section heading when cheaply recoverable

Do not break existing Phase 1 annotations.

## 3. Integration architecture

Introduce a small integration abstraction now so later WoS, Semantic Scholar, EndNote, Origin, Excel, VOSviewer, Stork, and other connectors do not become hard-coded branches.

Use capability-based adapters, for example:
- health/status
- search (when applicable)
- import
- export
- sync
- open external resource

Do not over-generalize into a plugin marketplace in Phase 2A. The goal is clean boundaries, not premature complexity.

Suggested source structure:
`backend/app/integrations/`
- `base.py`
- `zotero_local.py`
- `zotero_web.py`

Future integrations can implement the same capability contracts where appropriate.

## 4. Zotero modes

Support two modes behind one typed interface:

### 4.1 Zotero Local API
Preferred when Zotero desktop is running and local integration is available.

### 4.2 Zotero Web API v3
Optional cloud mode using user-authorized API credentials.

Never modify `zotero.sqlite` directly.

Required adapter operations:
- connection health/status
- identify library/account when safely available
- list collections
- fetch items
- create item
- update item safely
- tags
- notes
- attachment metadata
- attach/upload PDF where officially supported and permitted
- incremental synchronization

Use official APIs only.

## 5. Secure configuration

Settings must support:
- Enable Zotero
- Local / Web mode
- local endpoint/key if required
- Web library type: user/group
- library ID
- Web API key
- Test connection
- Clear/revoke credentials

Security rules:
- secrets in OS keyring only
- no secrets in SQLite
- no secrets in logs
- no secrets in backups
- no secrets in renderer localStorage
- backend performs authenticated Zotero calls
- renderer receives only status and non-secret configuration where practical

## 6. Sync identity and state

Add normalized Zotero sync state, including:
- ResearchOS work_id
- Zotero library identifier
- Zotero item key
- Zotero version
- last_synced_at
- local fingerprint
- last remote version
- sync status
- conflict status/details

Matching priority:
1. DOI
2. PMID/arXiv/other stable IDs
3. normalized title + authors + year
4. manual match

Never silently merge conflicting DOIs.

## 7. Import from Zotero

User workflow:
- connect Zotero
- choose all library or selected collection(s)
- preview
- import
- summary report

Preserve where available:
- title
- authors
- DOI and stable IDs
- journal/source
- publication date/year
- URL
- tags
- notes, clearly marked with origin
- collection membership
- attachment metadata

Summary counters:
- created
- matched
- updated
- skipped
- conflicts
- errors

Avoid duplicate Works.

### Zotero PDF handling
Distinguish:
- external Zotero attachment reference
- ResearchOS-managed copy

User may explicitly copy a Zotero PDF into ResearchOS managed storage.

If SHA-256 already exists in ResearchOS, link identity instead of duplicating bytes.

## 8. Export/push to Zotero

From ResearchOS allow:
- push one or multiple selected Works
- choose destination Zotero collection
- create item if absent
- update linked item safely
- send tags
- optionally send a clearly named ResearchOS note/material summary
- attach lawful PDF only where supported and authorized

Never blindly overwrite remote metadata.

## 9. Two-way incremental sync

States shown to user:
- Not linked
- In sync
- Local changes
- Remote changes
- Conflict
- Error

Rules:
- remote-only change → update local safely
- local-only change → push safely
- both changed → conflict; do not auto-overwrite
- DOI conflict → mandatory explicit user resolution

Conflict UI must support field-level comparison for:
- title
- authors
- DOI
- journal
- date/year
- tags
- notes
- collections

Actions:
- Keep ResearchOS
- Keep Zotero
- Merge where safe
- choose per field

Use Zotero versioning/optimistic concurrency when officially supported.

## 10. Collection mapping

ResearchOS and Zotero collections are distinct systems.

Provide:
- mapping table
- import source mapping
- export destination mapping
- optional mirror mode

If nested hierarchy cannot be mirrored cleanly, preserve remote hierarchy metadata and document the limitation rather than flattening silently.

## 11. Backup / restore / migration

Add `Settings > Storage & Backup`.

Backup bundle must contain:
- database
- managed attachments
- manifest

Manifest includes:
- app version
- schema version
- timestamp
- DB checksum
- attachment inventory + SHA-256

Requirements:
- validate before restore
- choose destination
- restore into a different absolute folder
- automatic pre-migration DB backup
- detect missing/corrupt managed attachments
- never include OS-keyring secrets

## 12. Diagnostics

Add a Library Diagnostics view with:
- schema version
- Work count
- attachment count
- managed/external attachment counts
- missing files
- duplicate hashes
- linked Zotero items
- sync conflicts
- last backup
- storage size

Repair actions only when safe and reversible.

## 13. Export interoperability

Implement:
- RIS
- BibTeX
- CSL-JSON

Scope:
- one Work
- selected Works
- collection
- full Library

This prepares future EndNote/Stork workflows.

## 14. UI requirement
`specs/UI_V2_SPEC.md` is mandatory and part of the Phase 2A acceptance gate.

Core design direction:
- global navigation on top
- no permanent left navigation rail
- collapsible/resizable left/right Reader panels
- Focus mode
- true Zen/full-screen mode
- Zotero top-level destination
- command palette

## 15. Explicitly deferred to later phases
Do NOT implement in Phase 2A:
- AI/LLM paper extraction
- vector embeddings/semantic search
- electrocatalysis structured extraction/dashboard
- Watch/Stork automation
- Review Studio
- citation network visualization
- manuscript critique
- OCR
- Web of Science/Semantic Scholar search adapters

## 16. Completion artifact
Create `PHASE2A_REPORT.md` with:
- implementation summary
- migrations
- security model
- Zotero API design
- UI redesign summary
- exact tests/results
- manual acceptance evidence
- known limitations
- latest commit SHA
- Windows artifact
- PASS/FAIL matrix

Do not merge Phase 2A PR before product-owner review.
