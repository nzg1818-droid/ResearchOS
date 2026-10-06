# ResearchOS — Codex Master Build Specification

## 0. Mission
Build a local-first Windows desktop application for scholarly literature discovery, lawful full-text acquisition, PDF reading, structured extraction, personal knowledge management, Zotero synchronization, literature alerts, and review-writing support.

The application should combine the useful workflows of Web of Science (federated search/filter/citation analytics), Zotero (personal library, attachments, collections, tags, annotations), and Stork (keyword alerts/reading guides), without copying their branding or visual design.

Target user: a materials/electrocatalysis PhD researcher. The default domain extraction schema must understand alkaline water electrolysis (AWE), HER, OER, UOR, EGOR, HMFOR, NiFe/NiMo/NiMoP/NiFeP/Ni(OH)x, self-supported electrodes, high-current-density testing, 1 M KOH and 30 wt% KOH, and device-level electrolysis.

This is not a paywall-bypass tool. Use official APIs and lawful access. Never store institutional usernames/passwords. Institutional full-text access must use user-controlled browser SSO / OpenURL / proxy linking and then auto-import downloaded PDFs.

## 1. Product principles
1. Local-first and privacy-first.
2. Every bibliographic item must have a canonical identity and provenance.
3. Every AI-extracted factual claim must link back to paper + page/section/table/figure + evidence snippet + confidence.
4. Metadata search and full-text acquisition are separate subsystems.
5. Deduplicate across all data sources before analysis.
6. Prefer official APIs over scraping.
7. Use modular adapters so databases can be added/removed.
8. Support online and local LLMs through one provider interface.
9. Never invent missing paper information. Mark fields as unknown.
10. Long-running jobs must be resumable and observable in a task queue.

## 2. Recommended stack
Desktop/UI:
- Electron
- React + TypeScript + Vite
- Material UI
- PDF.js
- ECharts or Plotly
- electron-builder

Local backend:
- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy / SQLModel
- SQLite + FTS5
- LanceDB for embeddings
- APScheduler
- httpx + tenacity
- PyMuPDF
- optional GROBID
- watchdog
- keyring
- pytest

Packaging:
- Python backend as a PyInstaller sidecar
- Electron launches/stops local backend
- core features require no cloud server

## 3. Core modules

### A. Federated Search
Search by keyword, exact title, author, DOI, ORCID, Boolean query, publication date, journal, document type, OA status, institution, citation count. Sort by relevance/newest/citations.

Adapters:
- OpenAlex: broad discovery backbone, citation graph, OA locations
- Crossref: DOI/canonical metadata validation
- Semantic Scholar: citation/recommendation enrichment
- PubMed/Europe PMC and arXiv as optional adapters
- Web of Science Starter/Expanded as optional adapters requiring authorized API credentials
- architecture must allow Scopus or other licensed sources later

Store raw source responses for reproducibility.

### B. Canonicalization and Deduplication
Canonical key priority:
1. DOI normalized lowercase
2. PMID/arXiv/OpenAlex/S2 IDs
3. normalized title + first author + year
4. PDF SHA-256
Implement field-level merge with conflict tracking.

### C. Full-text Acquisition
Priority:
1. existing local PDF
2. OA full text from repository/OA locations
3. publisher OA URL
4. institution-assisted browser flow

Institution flow:
- configure institution and optional OpenURL/proxy resolver
- open DOI/publisher in system browser
- user performs SSO/MFA
- app watches Downloads folder
- matching PDF is hashed, identified, imported and attached
- never automate password entry, bypass paywalls/CAPTCHAs, or circumvent access controls

Buttons:
Open DOI | Open publisher | Find OA copy | Open via institution | Attach PDF | Re-check full text

### D. Personal Library
Nested collections, tags, starred/unread/reading/completed status, custom fields, attachments, notes, duplicate review, batch metadata refresh, BibTeX/RIS/CSL-JSON export, CSV/XLSX export of structured data.

Folder watcher:
- watch Downloads/Papers
- identify new PDFs
- extract DOI/title
- match/create work
- configurable organization template

Never edit Zotero SQLite directly.

### E. Zotero Integration
Support:
1. Zotero local API
2. Zotero Web API v3

Capabilities:
- pull items, collections, tags, notes, attachment metadata
- push new bibliographic items
- update metadata with version checks
- upload/attach PDFs where allowed
- map collections
- SyncState table
- conflict UI

Secrets in OS keyring.

### F. PDF Reader + Annotation + Material Bank
PDF.js reader with text highlight, comments, figure/table rectangle annotation, "Save as evidence", "Save as writing material".

Every saved material stores:
work_id, DOI, title, authors/year, page, section, exact selected text, surrounding context, coordinates, user note, tags, created_at.

Material Bank views:
topic | paper | project | rhetorical role (background/mechanism/evidence/limitation/future direction/useful expression)

Clicking material jumps to exact PDF page/highlight.

Claim layer:
- claim = user or AI paraphrase
- claim links to one or more evidence materials
- provenance is never lost

### G. Structured Paper Extraction
Extraction levels:
metadata | abstract | full_text | full_text_verified

Output strict JSON with evidence for every nontrivial value.

General fields:
research question, catalyst/material, substrate, composition, synthesis, precursors, synthesis parameters, characterization, electrochemical methods, performance, stability, mechanism, evidence, novelty, limitations, unresolved questions, relevance.

Rules:
- reported vs AI inference must be explicit
- distinguish geometric/ECSA/mass-normalized current
- store reference electrode and RHE conversion
- store iR correction and percentage
- store electrolyte, concentration, temperature, pressure/flow
- store loading and area
- incompatible conditions must trigger comparison warnings

### H. Evidence-first AI
Create provider-agnostic LLMProvider.

Operations:
abstract summary, full-paper extraction, evidence linking, contradiction detection, research-gap synthesis, review outline, manuscript critique.

Save model/provider, prompt version, corpus IDs, timestamp, confidence, evidence links.

UI labels:
Reported by source | Computed by app | AI interpretation/hypothesis

### I. Watchlists / Alerts
WatchQuery fields:
name, search expression, adapters, date policy, journal/author filters, relevance threshold, dedup rules, schedule, notification settings.

Each run:
1. query enabled sources
2. merge/dedup
3. compare against prior runs
4. relevance-score
5. extract abstract/full text when available
6. generate digest
7. save
8. notify only for truly new relevant papers

Use Windows native notifications. Clicking opens Today Digest.

Stork interoperability:
- RIS import/export
- ingest exported Stork RIS
- optional ingestion of Stork alert emails via user-authorized email/OAuth
- no undocumented scraping
- deduplicate against local DB

### J. Review Studio
Workflow:
scope -> search strategy -> multi-source retrieval -> dedup -> inclusion/exclusion -> timeline -> citation network -> topic clustering -> evidence matrix -> benchmark tables -> contradictions -> gaps -> future hypotheses.

For uploaded review/manuscript:
- parse references and claims
- compare with chosen corpus
- flag outdated coverage
- flag missing seminal/recent papers
- flag unsupported generalizations
- flag over-reliance on one research group
- flag contradictory evidence not discussed
- suggest alternative review structures
- generate coverage report, not fake plagiarism/originality score

Every recommendation cites corpus papers.

### K. Electrocatalysis Dashboard
Filters:
HER/OER/UOR/EGOR/HMFOR, catalyst family, substrate, electrolyte, KOH concentration, temperature, synthesis method, current density, stability duration, journal/year.

Benchmark fields:
eta @ 10/100/500/1000/2000 mA cm-2
full-cell voltage @ 100/500/1000/2000 mA cm-2
Tafel slope, Rct, ECSA/Cdl, FE
stability current density + hours
product selectivity/yield
1 M KOH vs 30 wt% KOH
RT vs elevated temperature
flow/zero-gap/membrane/diaphragm

Never rank blindly across incompatible conditions.

## 4. Minimum database tables
works, authors, work_authors, sources, identifiers, source_hits, search_runs, files, collections, collection_works, tags, work_tags, notes, annotations, materials, claims, claim_evidence, extractions, electrochem_measurements, synthesis_steps, characterization_records, watch_queries, watch_runs, notifications, zotero_sync_state, llm_runs, review_projects, review_project_works, inclusion_decisions.

Use Alembic migrations.

## 5. Search relevance
Transparent score:
lexical relevance + semantic similarity + recency + journal priority + citation signal + user feedback.

Feedback:
Highly relevant | Relevant | Not relevant | Already known.

## 6. Security
- secrets in OS keyring
- no plaintext passwords
- institutional credentials never stored
- no Zotero DB modification
- no paywall/CAPTCHA bypass
- API rate limit + backoff
- audit log for external writes
- local backup/export

## 7. UI navigation
Search | Library | Reader | Knowledge | Watch | Reviews | Dashboard | Tasks | Settings

Search: filters + results + preview.
Library: collection tree + table + detail panel.
Reader: outline + PDF + evidence panel.
Knowledge: claims/highlights/materials with backlinks.
Watch: queries, schedules, last run, new count.
Reviews: corpus + timeline + citation network + evidence matrix + critique.
Dashboard: condition-aware benchmarks.
Tasks: job progress/log/retry/cancel.

## 8. Delivery phases
Phase 1:
app shell, SQLite schema, OpenAlex+Crossref search, dedup, library, DOI links, OA acquisition, PDF import, PDF reader, highlights/material bank.

Phase 2:
Zotero sync, structured extraction, electrocatalysis dashboard, semantic search.

Phase 3:
watchlists, Windows notifications, Stork RIS interop, optional WoS adapter, citation network, Review Studio.

Phase 4:
manuscript-corpus comparison, advanced synthesis, provider SDK, installer/updater/backups.

Implement vertical slices and test after each phase.

## 9. Acceptance tests
1. Search `NiFe LDH alkaline water electrolysis` between two dates and merge OpenAlex+Crossref without DOI duplicates.
2. Search exact DOI/title/author.
3. Click result -> DOI/publisher.
4. Find a lawful OA PDF when available.
5. Attach a manually downloaded institutional PDF and auto-match it.
6. Import 100 PDFs and deduplicate.
7. Push/pull Zotero test item without touching Zotero SQLite.
8. Save PDF highlight, restart, click material and jump to exact page.
9. Extract an electrocatalysis paper to strict JSON with evidence provenance.
10. Compare eta@500 and stability with condition warnings.
11. Run daily watch and show only newly discovered works.
12. Generate evidence-backed review corpus report with no uncited AI claims.
13. Pass backend unit and frontend smoke tests.
14. Build Windows installer.

## 10. Codex execution rules
- first generate ARCHITECTURE.md, ROADMAP.md, .env.example, DB migrations
- then implement Phase 1 only
- run tests and fix failures before Phase 2
- adapters behind interfaces
- use official APIs over scraping
- do not request institutional passwords
- typed models
- changelog
- mock API fixtures
- demo dataset
- DEV_SETUP.md with Windows commands
- USER_GUIDE.md
- after each phase report implemented features, tests, limitations, next tasks

## 11. First action
Create the repository and implement Phase 1. Do not merely describe code. Generate working files, run tests, fix errors, and show exact Windows launch commands.
