# ResearchOS Phase 2B1 — Paper Intelligence Core

## 0. Status and scope

Phase 2A / v0.2 is the accepted baseline. Phase 2B1 must start from merged `main` and must not re-implement or regress Phase 1/2A features.

This phase turns ResearchOS from a literature manager into an evidence-first paper-reading system.

Target workflow:

`PDF / abstract -> deterministic parse -> structured document model -> evidence-aware AI extraction -> human verification -> reusable knowledge`

Phase 2B1 is deliberately narrower than the full Research Intelligence vision. It implements reliable paper understanding and evidence provenance. Cross-paper benchmarking, ranking, research-gap analytics, Watch/Stork monitoring, citation-network visualization and review synthesis belong to Phase 2B2/3.

## 1. Product principles

1. Source text is the authority; AI output is never the authority.
2. Every nontrivial extracted claim or numeric value must point to evidence.
3. Missing information must remain `unknown`, not be guessed.
4. Reported values, app-computed values and AI interpretations must be visibly different.
5. Full-text and abstract-only analyses must never be presented as equivalent.
6. Cloud AI is opt-in per paper/batch; local AI is supported through the same provider interface.
7. Expensive AI runs are cached and reproducible by document hash + schema version + prompt version + provider/model.
8. ResearchOS must remain useful without AI: parsing, FTS, evidence links and manual materials work offline.
9. The user must be able to verify/edit/reject every extracted field.
10. No hidden chain-of-thought is requested, stored, displayed or required. Store concise evidence/rationale only.

## 2. Carry-forward Phase 2A polish

Before AI work, fix these small accepted Phase 2A items:

### 2.1 Zotero Web onboarding
- Add a `Use API key to identify account` flow using official `GET https://api.zotero.org/keys/current` with the key in the `Zotero-API-Key` header.
- Display detected username, numeric user ID and granted permissions.
- Let the user create/update the personal-library connection without manually finding the user ID.
- Never place the API key in a URL, DB, log or renderer localStorage.

### 2.2 Local Zotero re-authorization
- If a local write returns 401 and the stored local key was single-use/expired, surface `Re-authorize Zotero Local write access` instead of a generic failure.
- Do not loop authorization prompts automatically.

### 2.3 Frontend cleanup
- Remove the existing MUI out-of-range connection-select warning in tests.
- Keep bundle splitting; lazy-load Phase 2B1 Intelligence screens and heavy parsing/visual components.

## 3. Document ingestion and parsing

### 3.1 Document status
Each Work/file can have one parsing state:
- Not parsed
- Parsing
- Parsed
- Abstract only
- Needs OCR
- Parse failed

### 3.2 Full-text parser
Use PyMuPDF as the primary local parser.

For each PDF capture:
- page number
- page plain text
- ordered text blocks
- block bounding boxes normalized to page coordinates
- likely section heading for each block where feasible
- table/figure caption candidates
- document text hash
- parser version

Do not OCR in this phase. Detect image-only/scanned pages and mark `Needs OCR` with a clear user message.

### 3.3 Section model
Infer common scholarly sections conservatively:
- Abstract
- Introduction
- Experimental / Methods
- Results and Discussion
- Characterization
- Electrochemical Measurements
- Conclusions
- Supporting/Other

Section detection may be heuristic. Store detected heading text and confidence. Never fabricate missing sections.

### 3.4 Chunks
Create stable chunks for retrieval/extraction.

Each chunk stores:
- document/file ID
- Work ID
- page start/end
- block IDs
- heading/section
- text
- normalized page bbox list when applicable
- chunk hash
- token/character length

Chunk IDs should remain stable when the same PDF is reparsed with the same parser version.

### 3.5 Abstract-only fallback
If no usable PDF exists:
- use the best available abstract already present or retrieved by existing metadata adapters
- mark extraction level `abstract`
- disable fields that cannot responsibly be inferred from an abstract
- visibly label every result `Abstract-only analysis`

## 4. Database additions

Use Alembic migrations. Suggested normalized entities:

- `paper_documents`
  - id, work_id, file_id nullable, source_type, parser_version, text_hash, parse_status, page_count, has_text_layer, created_at, updated_at
- `document_pages`
  - document_id, page_number, text, width, height
- `document_blocks`
  - document_id, page_number, block_index, section, heading, text, bbox_json, hash
- `document_chunks`
  - document_id, order_index, page_start, page_end, section, heading, text, bbox_json, hash
- `extraction_runs`
  - work_id, document_id, extraction_level, schema_version, prompt_version, provider_id, model, source_hash, status, started_at, finished_at, error
- `paper_extractions`
  - run_id, payload_json, verification_status, created_at
- `evidence_anchors`
  - extraction_id, field_path, chunk_id nullable, file_id nullable, page, section, quote, bbox_json, evidence_type, confidence, validation_status
- `verification_decisions`
  - extraction_id, field_path, action, old_value_json, new_value_json, user_note, created_at
- `ai_provider_configs`
  - non-secret provider configuration only
- `ai_runs`
  - provider/model/prompt/schema/source hashes, request metadata, token usage when returned, cache key, status/error, timestamps
- `paper_questions`
- `paper_answers`

Secrets remain in OS keyring only.

## 5. AI provider architecture

Create a typed `LLMProvider` interface. Provider-specific code must not leak into extraction logic.

Required capabilities:
- health/test connection
- structured JSON generation
- text answer generation
- optional token-usage reporting

Initial adapters:
1. `OpenAICompatibleProvider` for configurable HTTPS OpenAI-compatible endpoints.
2. `OllamaProvider` for a loopback local endpoint.
3. `MockProvider` for deterministic tests.

Do not make any cloud provider mandatory for core app startup.

Provider settings:
- display name
- provider type
- endpoint (allowlisted validation: HTTPS for remote; loopback HTTP for local)
- model name
- max output tokens
- timeout
- concurrency
- enabled
- cloud/local classification

API keys/tokens live in keyring only.

## 6. Privacy and cost controls

### 6.1 Cloud consent
Before sending PDF-derived text to a remote provider, require explicit user consent:
- one paper
- selected batch
- optionally `remember for this session`, not forever by default

Show:
- provider/model
- cloud vs local
- number of pages/chunks
- approximate input size

No background job may silently send a newly imported PDF to cloud AI.

### 6.2 Caching
Use cache key based on:
`document/source hash + extraction schema version + prompt version + provider type + model + relevant settings`

If an identical successful result exists, offer `Use cached result` by default.

### 6.3 Batch limits
- configurable concurrency
- pause/cancel/retry
- per-paper error isolation
- resumable job state
- no batch of thousands by default; require explicit confirmation above a sensible threshold

## 7. Extraction levels

Four explicit levels:
- `metadata`
- `abstract`
- `full_text`
- `full_text_verified`

A result can move upward but must retain prior run provenance.

## 8. Core structured extraction schema

All results use strict Pydantic/JSON schema validation.

### 8.1 General paper fields
- research question
- study objective
- paper type
- materials/catalysts
- substrate/support
- synthesis route
- characterization methods and major findings
- electrochemical/experimental methods
- key reported results
- mechanism/theory claims
- evidence used to support mechanism
- novelty/highlights
- limitations
- unresolved questions
- industrial/scaling relevance

### 8.2 Material records
For each material:
- canonical display name
- composition
- dopants
- support/substrate
- morphology
- phase
- amorphous/crystalline/mixed/unknown
- interface/heterostructure description
- role (catalyst/precatalyst/support/reference/control)

### 8.3 Synthesis records
For each ordered step where available:
- method
- precursor/reagent names
- concentrations
- solvent/electrolyte
- potential/current/current density
- reference electrode
- time
- temperature
- pressure
- atmosphere
- pH
- annealing/phosphidation/sulfidation/nitridation parameters
- scale/area
- notes

### 8.4 Characterization records
- method (SEM/TEM/XRD/XPS/XAS/Raman/FTIR/ICP/etc.)
- ex situ / in situ / operando
- sample state (as-prepared/activated/working/post-test)
- finding
- mechanism relevance

### 8.5 Electrochemistry records
- reaction: HER/OER/UOR/EGOR/HMFOR/overall water splitting/other
- three-electrode/two-electrode/flow/zero-gap/etc.
- electrolyte composition and concentration
- KOH concentration original text + normalized representation
- temperature
- pressure
- flow condition/rate
- working/counter/reference electrode
- reference conversion details
- geometric area
- loading
- geometric/ECSA/mass-normalized basis
- iR correction yes/no/unknown and percentage/method
- scan rate
- rotation/agitation if relevant

### 8.6 Performance measurements
Represent measurements as individual rows, not a single prose field:
- metric type
- reported value
- reported unit
- normalized numeric value/unit when safely possible
- current density
- potential/overpotential/cell voltage
- duration
- product
- Faradaic efficiency
- selectivity
- yield/conversion
- Tafel slope
- Rct
- Cdl/ECSA
- retention/degradation
- normalization basis
- condition reference

High-priority current-density anchors for water electrolysis:
10, 100, 500, 1000, 2000 mA cm^-2 when explicitly reported or safely interpolated only if the user explicitly requests computation. Do not invent/interpolate during default extraction.

### 8.7 Mechanism claims
Each mechanism record:
- claim
- source-reported vs AI interpretation
- evidence types
- supporting characterization/DFT/kinetics
- working-state vs ex-situ distinction
- confidence

## 9. Evidence-first contract

Every nontrivial extracted field must support zero or more anchors. Required fields and numeric performance values must have at least one anchor to be considered `evidenced`.

Anchor stores:
- Work/file
- page
- section/heading
- exact source snippet
- chunk/block ID
- normalized bbox where available
- evidence type
- confidence

Clicking an anchor must open Reader at the page and visually focus the relevant area/text.

### 9.1 Evidence validation
Implement deterministic post-validation:
- numeric value should appear in the cited snippet/context after tolerant formatting normalization, or be explicitly marked `computed`
- units should be compatible with extracted metric
- cited page must exist
- evidence snippet must occur in page/chunk text
- if evidence is absent/mismatched: mark `Needs review`, never silently PASS

### 9.2 Status labels
Every claim/value is one of:
- `source_reported`
- `app_computed`
- `ai_interpretation`

Every field is one of:
- Unverified
- Evidence matched
- Needs review
- User verified
- User corrected
- Rejected

## 10. Scientific validity rules

These are product rules, not prompt-only suggestions.

1. Unknown iR correction stays unknown.
2. Unknown current-density normalization stays unknown.
3. Do not convert to RHE unless inputs are sufficient; any conversion is `app_computed` with formula/inputs recorded.
4. Do not equate OER precatalyst composition with working-state active phase.
5. Do not infer ideal UOR products from current alone.
6. EGOR/HMFOR performance requires product/FE/selectivity context where the paper reports it.
7. Do not compare/rank incompatible electrolytes, temperatures or normalization bases in this phase.
8. Abstract-only extraction must not fabricate synthesis recipes or detailed electrochemical settings.
9. `amorphous = better` and `more elements = better` are not allowed as automatic conclusions.
10. If the paper's mechanism evidence is only ex-situ, label that limitation.

## 11. Prompt architecture

Prompts are versioned files/templates in the repository, not giant inline strings scattered in code.

Use multi-stage extraction to reduce cost and hallucination:
1. document map / relevant-section selection
2. deterministic candidate extraction for obvious metadata/numbers where useful
3. targeted structured extraction by schema section
4. evidence linking
5. deterministic validator
6. optional concise synthesis

Do not repeatedly send the whole PDF when relevant chunks suffice.

## 12. Paper Intelligence UI

Add an `Intelligence` experience accessible from Library and Reader.

### 12.1 Reader right-panel tabs
- Evidence
- Notes
- Materials
- Intelligence
- Ask Paper

### 12.2 Intelligence summary
Sections:
- One-minute brief
- Research question
- Materials
- Synthesis
- Characterization
- Electrochemistry
- Performance
- Mechanism
- Highlights
- Limitations
- Industrial relevance

Each extracted row shows:
- value
- status chip
- confidence
- source page button
- Verify
- Edit
- Reject

### 12.3 Evidence interaction
Click `p. 6` / `Show evidence`:
- opens exact PDF page
- focuses evidence bbox/text
- keeps Intelligence panel open

### 12.4 Verification workflow
User can:
- Accept field
- Edit field
- Reject field
- Add note
- save an evidence-backed claim/material to Knowledge

Never overwrite the original AI extraction; store a verification decision/version.

## 13. Ask Paper

Implement paper-scoped Q&A using only parsed content for that Work by default.

Requirements:
- retrieve relevant chunks with SQLite FTS5 initially
- answer with clickable page citations
- show cited snippets in an evidence drawer
- say `Not found in this paper` when evidence is insufficient
- do not silently use web search or other papers
- user can save an answer/claim to Knowledge only with attached evidence anchors

Semantic embeddings are deferred to Phase 2B2 unless they can be added without destabilizing this phase.

## 14. Knowledge integration

Existing Knowledge/Material Bank remains source-centered.

Add:
- save verified extraction field as claim/material
- link one claim to multiple evidence anchors from the same paper
- preserve Work/page provenance
- distinguish user-written claim from AI-generated claim

Cross-paper claim aggregation is Phase 2B2.

## 15. Batch paper processing

Library supports selecting multiple Works and choosing:
- Parse documents
- Extract abstracts
- Extract full text

Batch view shows:
- queued/running/completed/failed/cached/needs review
- per-paper progress
- cancel/pause/retry
- provider/model
- cloud/local indicator

A bad PDF or provider failure must not abort the rest of the batch.

## 16. Settings > AI

Add:
- provider list
- Add provider
- type
- endpoint
- model
- secret/key entry
- cloud/local label
- Test connection
- default provider
- default extraction level
- concurrency
- privacy defaults
- cache controls

No provider secret in renderer persistent storage.

## 17. Export

For one Work or selected Works export structured intelligence as:
- JSON
- CSV (flattened measurement/extraction tables)

Preserve IDs and evidence page references. XLSX and publication-ready benchmark export are deferred to Phase 2B2.

## 18. Error handling

User-visible errors should distinguish:
- no PDF
- abstract only
- scanned/needs OCR
- parser failed
- provider not configured
- provider auth error
- rate limit
- provider timeout
- invalid structured output
- evidence mismatch
- cancelled

Retries must be idempotent and cache-aware.

## 19. Performance targets

- Parsing a typical text PDF should not block the UI.
- Reader remains responsive while parsing/extraction runs.
- FTS Ask Paper retrieval over one typical paper should feel interactive.
- Opening a previously cached extraction should not trigger network calls.
- 50-paper batch must be resumable and memory-bounded.

## 20. Explicitly deferred

Do not implement in Phase 2B1:
- cross-paper performance ranking
- full Electrocatalysis Dashboard
- research-gap engine
- field-wide trend synthesis
- embeddings/vector DB unless strictly needed
- Watch/Stork daily monitoring
- Web of Science adapter expansion
- citation-network visualization
- automated review writing
- manuscript corpus critique
- OCR
- automatic figure/table vision interpretation

## 21. Completion deliverables

Create:
- Alembic migration(s)
- `PHASE2B1_REPORT.md`
- updated `ARCHITECTURE.md`
- updated `USER_GUIDE.md`
- prompt-template directory with versioned templates
- mock provider fixtures
- sample electrocatalysis extraction fixture
- Windows CI/build artifact

Do not merge the Phase 2B1 PR until formal Product Owner review.