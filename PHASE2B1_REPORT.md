# ResearchOS Phase 2B1 / Paper Intelligence report

Status: **PARTIAL — real-paper / real-provider manual acceptance pending.** No merge authorized. No Phase 2B2/3 implementation.

Branch: `feat/phase2b1-paper-intelligence`, based on the existing specification branch from accepted Phase 2A main. Kickoff and references read in order. Baseline recorded in `docs/phase2b1-baseline.md`: 36 backend / 11 frontend passed.

## Delivery and verification

Vertical slices: Zotero onboarding/reauthorization; 0003 schema + parsing/FTS; typed providers + versioned schema/prompts + deterministic validation; Reader review/Ask + Knowledge + resumable batches + export; Windows packaging and evidence report.

Latest local suite: **52 backend tests, 17 frontend tests passed**, TypeScript passed. One upstream Starlette/httpx deprecation warning remains. Vite emits an advisory main-chunk size warning; Intelligence, AISettings, Reader and PDF worker are separate chunks.

```powershell
# backend
../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
# repository root
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vitest/vitest.mjs run --pool=threads --configLoader native
./scripts/build-windows.ps1
.venv/Scripts/python.exe scripts/verify_phase2b1_package.py
```

Windows package: `release/ResearchOS-0.3.0-win-x64.zip`, SHA-256 in adjacent `.sha256`. Extract all files and run `ResearchOS-0.3.0-portable/ResearchOS.exe`. No Python/Node required on the destination machine. Unsigned portable executable. `release/phase2b1-frozen-smoke.json` records isolated packaged-sidecar checks; these exercise the packaged prompts and local Mock, not a real cloud model.

Published implementation `c0a682e6716d53c2d327a96c75b04e7ff70c2c82` passed [Windows CI 38219956334](https://github.com/nzg1818-droid/ResearchOS/actions/runs/38219956334), including all backend/frontend tests, packaging, frozen smoke and artifact upload. That run had 16 frontend tests; the subsequent Library entry-point correction adds the 17th local frontend regression. The PR checks and delivered validation manifest identify the final follow-up run.

## Migration and privacy

Migration 0003 adds normalized document/extraction/evidence/review/AI/Q&A entities and paper-scoped FTS5, preserving Phase 2A records. A 0002→0003 regression checks the original Work and pre-migration SQLite snapshot. Backups/restores accept 0002 and 0003. Original PDFs are never changed. Restore the pre-migration backup into a new directory to downgrade.

Secrets are OS-keyring-only; non-secret provider configuration lives in SQLite. Canary tests inspect backup contents, logs and renderer persistence. Remote endpoints require HTTPS; local Ollama requires loopback HTTP. Redirects are disabled. Changing endpoint clears the old key. Cloud consent is required on each paper/batch execution and again after resume; historical consent metadata does not grant future permission. Imported papers do not auto-trigger AI. Invalid output and errors are sanitized; chain-of-thought is neither requested nor retained.

## Acceptance matrix

PASS reflects the stated evidence boundary. Mock/API/component evidence is not a native or real-provider manual pass.

| # | Result | Requirement | Evidence |
|---|---|---|---|
| 1 | PASS | All Phase 2A backend tests still pass. | Full original regression suites retained; Zotero, annotations/backlinks, backup, search/import tests pass. Native Phase 2B1 manual checks remain separate. |
| 2 | PASS | All Phase 2A frontend tests still pass. | Full original regression suites retained; Zotero, annotations/backlinks, backup, search/import tests pass. Native Phase 2B1 manual checks remain separate. |
| 3 | PASS | Windows portable build still succeeds. | Local build-windows.ps1 succeeds; frozen sidecar synthetic import/extract/Ask smoke passes. Windows CI 38219956334 also passed packaging and frozen smoke. |
| 4 | PASS | Search/Library/Reader/Knowledge/Zotero/backup remain functional. | Full original regression suites retained; Zotero, annotations/backlinks, backup, search/import tests pass. Native Phase 2B1 manual checks remain separate. |
| 5 | PASS | Zotero Web key introspection can identify/validate personal user ID and permissions without putting the key in URLs/logs/storage. | test_account_introspection_allowlists_response / test_local_write_auth_expiry_is_actionable_without_retry; official endpoint, header-only secret and one request asserted. |
| 6 | PASS | Local Zotero 401 presents a clear re-authorization path. | test_account_introspection_allowlists_response / test_local_write_auth_expiry_is_actionable_without_retry; official endpoint, header-only secret and one request asserted. |
| 7 | PASS | Existing MUI out-of-range warning is removed. | Connection select falls back to empty until its option exists; frontend suite has no out-of-range warning. |
| 8 | PASS | Text PDF creates a paper_document record. | test_parse_pages_geometry_cache_and_scoped_fts and test_abstract_scanned_failure_and_changed_source: pages, normalized geometry, sections, stable chunks/cache and text hash. |
| 9 | PASS | All PDF pages are represented with correct page numbers. | test_parse_pages_geometry_cache_and_scoped_fts and test_abstract_scanned_failure_and_changed_source: pages, normalized geometry, sections, stable chunks/cache and text hash. |
| 10 | PASS | Text blocks retain normalized bbox coordinates. | test_parse_pages_geometry_cache_and_scoped_fts and test_abstract_scanned_failure_and_changed_source: pages, normalized geometry, sections, stable chunks/cache and text hash. |
| 11 | PASS | Stable chunks are produced in reading order. | test_parse_pages_geometry_cache_and_scoped_fts and test_abstract_scanned_failure_and_changed_source: pages, normalized geometry, sections, stable chunks/cache and text hash. |
| 12 | PASS | Chunks retain page and section/heading provenance. | test_parse_pages_geometry_cache_and_scoped_fts and test_abstract_scanned_failure_and_changed_source: pages, normalized geometry, sections, stable chunks/cache and text hash. |
| 13 | PASS | Reparse of identical file/parser version is idempotent or cache-reused. | test_parse_pages_geometry_cache_and_scoped_fts and test_abstract_scanned_failure_and_changed_source: pages, normalized geometry, sections, stable chunks/cache and text hash. |
| 14 | PASS | Text hash changes when source text changes. | test_parse_pages_geometry_cache_and_scoped_fts and test_abstract_scanned_failure_and_changed_source: pages, normalized geometry, sections, stable chunks/cache and text hash. |
| 15 | PASS | Image-only/scanned PDF is marked Needs OCR rather than falsely Parsed. | No-text PDF yields Needs OCR; damaged PDF yields Parse failed, independently of other batch items. |
| 16 | PASS | Parser failure is isolated and user-visible. | No-text PDF yields Needs OCR; damaged PDF yields Parse failed, independently of other batch items. |
| 17 | PASS | Parsing runs off the UI thread/background task path. | Parsing runs via asyncio.to_thread in bounded background workers; routes return task IDs. |
| 18 | PASS | Strict versioned extraction schema exists. | Strict Pydantic PaperExtraction v1 with typed ordered records, null defaults, field origin/confidence/evidence; exported JSON schema and synthetic fixture committed. |
| 19 | PASS | Metadata extraction level works. | test_metadata_abstract_levels_and_restart_review; UI labels Abstract-only analysis and leaves detailed settings null. |
| 20 | PASS | Abstract extraction level works and is visibly marked abstract-only. | test_metadata_abstract_levels_and_restart_review; UI labels Abstract-only analysis and leaves detailed settings null. |
| 21 | PASS | Full-text extraction level works. | test_extraction_evidence_cache_review_export_and_ask plus frozen executable smoke complete full-text path using deterministic Mock. |
| 22 | PASS | Full-text verified state is distinct from ordinary full-text extraction. | test_all_verified_full_text_promotes_without_losing_run verifies distinct full_text_verified state and retained payload/run. |
| 23 | PASS | Materials are represented structurally, not prose-only. | Strict Pydantic PaperExtraction v1 with typed ordered records, null defaults, field origin/confidence/evidence; exported JSON schema and synthetic fixture committed. |
| 24 | PASS | Synthesis steps are ordered and structured. | Strict Pydantic PaperExtraction v1 with typed ordered records, null defaults, field origin/confidence/evidence; exported JSON schema and synthetic fixture committed. |
| 25 | PASS | Characterization records distinguish ex-situ/in-situ/operando when reported. | Strict Pydantic PaperExtraction v1 with typed ordered records, null defaults, field origin/confidence/evidence; exported JSON schema and synthetic fixture committed. |
| 26 | PASS | Electrochemical conditions are structured. | Strict Pydantic PaperExtraction v1 with typed ordered records, null defaults, field origin/confidence/evidence; exported JSON schema and synthetic fixture committed. |
| 27 | PASS | Performance measurements are row-oriented structured records. | Strict Pydantic PaperExtraction v1 with typed ordered records, null defaults, field origin/confidence/evidence; exported JSON schema and synthetic fixture committed. |
| 28 | PASS | Mechanism claims distinguish source_reported from ai_interpretation. | Strict Pydantic PaperExtraction v1 with typed ordered records, null defaults, field origin/confidence/evidence; exported JSON schema and synthetic fixture committed. |
| 29 | PASS | Unknown fields remain unknown/null rather than being filled speculatively. | Strict Pydantic PaperExtraction v1 with typed ordered records, null defaults, field origin/confidence/evidence; exported JSON schema and synthetic fixture committed. |
| 30 | PASS | Schema-invalid model output is rejected/repaired through a bounded path and never silently persisted as valid. | test_invalid_schema_failure_isolated_and_force_versions: unknown output rejected, sanitized failed run saved, no valid extraction persisted; no unbounded repair loop. |
| 31 | PASS | Every persisted numeric performance value has at least one evidence anchor or explicit Needs review status. | test_mismatched_output_never_becomes_verified: 999 vs source 250 persists Needs review, cannot be accepted, can be rejected/corrected without altering original payload. |
| 32 | PASS | Evidence anchor has Work/file/page/snippet provenance. | test_numeric_unit_and_foreign_anchor_rejected and parser integration: same-document chunk, page and quote required; bboxes come from parser, never model. |
| 33 | PASS | Evidence anchor page exists. | test_numeric_unit_and_foreign_anchor_rejected and parser integration: same-document chunk, page and quote required; bboxes come from parser, never model. |
| 34 | PASS | Evidence snippet can be matched back to parsed source text. | test_numeric_unit_and_foreign_anchor_rejected and parser integration: same-document chunk, page and quote required; bboxes come from parser, never model. |
| 35 | PASS | Evidence bbox is stored where parser coordinates permit it. | test_numeric_unit_and_foreign_anchor_rejected and parser integration: same-document chunk, page and quote required; bboxes come from parser, never model. |
| 36 | PASS | Clicking evidence opens correct PDF page. | Intelligence source-button interaction and Reader highlight/zoom test assert exact file/page and normalized overlay; real PDF visual acceptance still pending. |
| 37 | PASS | Evidence focus remains aligned after Reader zoom. | Intelligence source-button interaction and Reader highlight/zoom test assert exact file/page and normalized overlay; real PDF visual acceptance still pending. |
| 38 | PASS | Numeric evidence validator catches a deliberately hallucinated/mismatched value. | test_mismatched_output_never_becomes_verified: 999 vs source 250 persists Needs review, cannot be accepted, can be rejected/corrected without altering original payload. |
| 39 | PASS | Unit incompatibility produces Needs review instead of silent acceptance. | Unit mismatch test plus scientific metric/unit compatibility rules produce Needs review. |
| 40 | PASS | source_reported/app_computed/ai_interpretation are visibly distinct in UI and data. | Typed origin enum persisted; Intelligence renders source_reported/app_computed/ai_interpretation chips. No default computation action exists. |
| 41 | PASS | User can Accept an extracted field. | Accept/reject/correct integration tests; immutable extraction payload; timestamped field decisions; reopen with fresh DB session preserves User corrected. |
| 42 | PASS | User can Edit an extracted field. | Accept/reject/correct integration tests; immutable extraction payload; timestamped field decisions; reopen with fresh DB session preserves User corrected. |
| 43 | PASS | User can Reject an extracted field. | Accept/reject/correct integration tests; immutable extraction payload; timestamped field decisions; reopen with fresh DB session preserves User corrected. |
| 44 | PASS | Original extraction remains auditable after correction. | Accept/reject/correct integration tests; immutable extraction payload; timestamped field decisions; reopen with fresh DB session preserves User corrected. |
| 45 | PASS | Verification decision stores timestamp and field path. | Accept/reject/correct integration tests; immutable extraction payload; timestamped field decisions; reopen with fresh DB session preserves User corrected. |
| 46 | PASS | User verified/corrected status persists after restart. | Accept/reject/correct integration tests; immutable extraction payload; timestamped field decisions; reopen with fresh DB session preserves User corrected. |
| 47 | PASS | Verified field can be saved to Knowledge with source evidence. | Verified numeric field saves to Knowledge with annotation, Work/file/page and multiple-anchor provenance; old material backlink regression preserved. |
| 48 | PASS | Typed provider interface exists. | Typed LLMProvider plus deterministic Mock and HTTP MockTransport protocol tests cover HTTPS chat-completions, loopback Ollama, model health and sanitized auth/429/timeout errors. |
| 49 | PASS | Mock provider drives CI deterministically. | Typed LLMProvider plus deterministic Mock and HTTP MockTransport protocol tests cover HTTPS chat-completions, loopback Ollama, model health and sanitized auth/429/timeout errors. |
| 50 | PASS | OpenAI-compatible configurable provider path exists. | Typed LLMProvider plus deterministic Mock and HTTP MockTransport protocol tests cover HTTPS chat-completions, loopback Ollama, model health and sanitized auth/429/timeout errors. |
| 51 | PASS | Ollama/loopback local provider path exists. | Typed LLMProvider plus deterministic Mock and HTTP MockTransport protocol tests cover HTTPS chat-completions, loopback Ollama, model health and sanitized auth/429/timeout errors. |
| 52 | PASS | App works without any AI provider configured. | Application starts and parses/FTS retrieves with no provider. Import path never schedules extraction; extraction requires explicit batch request. |
| 53 | PASS | Provider secrets are stored in OS keyring only. | Cloud consent/endpoint/keyring canary test scans backup database and logs; frontend canary stays out of localStorage. HTTPS remote / loopback HTTP local validation enforced. |
| 54 | PASS | Canary provider secret is absent from SQLite/logs/backups/renderer localStorage. | Cloud consent/endpoint/keyring canary test scans backup database and logs; frontend canary stays out of localStorage. HTTPS remote / loopback HTTP local validation enforced. |
| 55 | PASS | Remote endpoint validation requires HTTPS except loopback-local providers. | Cloud consent/endpoint/keyring canary test scans backup database and logs; frontend canary stays out of localStorage. HTTPS remote / loopback HTTP local validation enforced. |
| 56 | PASS | Test connection reports provider/model status without exposing secret. | Typed LLMProvider plus deterministic Mock and HTTP MockTransport protocol tests cover HTTPS chat-completions, loopback Ollama, model health and sanitized auth/429/timeout errors. |
| 57 | PASS | Cloud-vs-local provider is explicit in UI. | Frontend consent test blocks until input preview and explicit checkbox; backend rejects cloud extraction without consent. UI shows provider/model/cloud and approximate size. |
| 58 | PASS | Remote/cloud extraction requires explicit user consent before PDF-derived text is sent. | Frontend consent test blocks until input preview and explicit checkbox; backend rejects cloud extraction without consent. UI shows provider/model/cloud and approximate size. |
| 59 | PASS | No newly imported PDF triggers cloud AI automatically. | Application starts and parses/FTS retrieves with no provider. Import path never schedules extraction; extraction requires explicit batch request. |
| 60 | PASS | AI run records provider/model/prompt/schema/source hashes. | AI/extraction run records retain provider/model, schema/prompt/source/cache hashes and request metadata; Ask records returned token usage and run provenance. |
| 61 | PASS | Identical successful extraction is cache-reused by default. | Cache reuse/force/schema/prompt invalidation tests. Source bytes/parser version also participate to preserve evidence geometry. |
| 62 | PASS | User can force re-run. | Cache reuse/force/schema/prompt invalidation tests. Source bytes/parser version also participate to preserve evidence geometry. |
| 63 | PASS | Prompt version change invalidates the relevant cache key. | Cache reuse/force/schema/prompt invalidation tests. Source bytes/parser version also participate to preserve evidence geometry. |
| 64 | PASS | Schema version change invalidates the relevant cache key. | Cache reuse/force/schema/prompt invalidation tests. Source bytes/parser version also participate to preserve evidence geometry. |
| 65 | PASS | Batch processing isolates per-paper failures. | 50-paper synthetic mixed text/abstract batch test isolates failure, resumes completed entries without duplicate documents and records peak traced memory <100 MiB. |
| 66 | PASS | Batch processing supports cancel or pause/resume/retry semantics consistent with the existing task architecture. | test_pause_cancel_and_resume_batch: paused/cancelled state persists and resume completes. In-flight requests finish safely before scheduling stops. |
| 67 | PASS | Interrupted batch can resume without duplicating completed extractions. | 50-paper synthetic mixed text/abstract batch test isolates failure, resumes completed entries without duplicate documents and records peak traced memory <100 MiB. |
| 68 | PASS | 50-paper synthetic batch is memory-bounded and does not crash. | 50-paper synthetic mixed text/abstract batch test isolates failure, resumes completed entries without duplicate documents and records peak traced memory <100 MiB. |
| 69 | PASS | Unknown iR correction remains unknown. | test_scientific_rules_abstract_and_unknowns: null iR/basis/conversion, abstract detail suppression and explicit ex-situ-only mechanism limitation. |
| 70 | PASS | Unknown normalization basis remains unknown. | test_scientific_rules_abstract_and_unknowns: null iR/basis/conversion, abstract detail suppression and explicit ex-situ-only mechanism limitation. |
| 71 | PASS | RHE conversion is not performed without sufficient inputs. | test_scientific_rules_abstract_and_unknowns: null iR/basis/conversion, abstract detail suppression and explicit ex-situ-only mechanism limitation. |
| 72 | PASS | Any app-computed conversion records formula/inputs and status. | No app-computed conversion action is implemented. Formula/inputs/origin exist in schema; model-proposed computed values always need review and cannot be verified as source-reported. |
| 73 | PASS | Precatalyst composition is not automatically asserted as the working-state active phase. | No default phase/product derivation; null defaults. Product/composition/phase must be explicitly present in cited source, with unsupported working-phase assertions flagged. Live scientific quality remains manual. |
| 74 | PASS | UOR current alone does not produce a claimed product distribution. | No default phase/product derivation; null defaults. Product/composition/phase must be explicitly present in cited source, with unsupported working-phase assertions flagged. Live scientific quality remains manual. |
| 75 | PASS | EGOR/HMFOR product metrics preserve FE/selectivity/yield context when reported. | Structured performance fields retain product, FE, selectivity, yield/conversion and conditions without ranking or invented interpolation. |
| 76 | PASS | Abstract-only mode does not fabricate synthesis recipes. | test_scientific_rules_abstract_and_unknowns: null iR/basis/conversion, abstract detail suppression and explicit ex-situ-only mechanism limitation. |
| 77 | PASS | Ex-situ-only mechanism evidence is labeled as such. | test_scientific_rules_abstract_and_unknowns: null iR/basis/conversion, abstract detail suppression and explicit ex-situ-only mechanism limitation. |
| 78 | PASS | Reader has an Intelligence tab/panel. | Reader Intelligence/Ask tabs and structured sections implemented; frontend tests exercise brief/field origin/status/confidence, evidence and verification actions. |
| 79 | PASS | Reader has an Ask Paper tab/panel. | Reader Intelligence/Ask tabs and structured sections implemented; frontend tests exercise brief/field origin/status/confidence, evidence and verification actions. |
| 80 | PASS | One-minute brief renders from the latest extraction. | Reader Intelligence/Ask tabs and structured sections implemented; frontend tests exercise brief/field origin/status/confidence, evidence and verification actions. |
| 81 | PASS | Materials/Synthesis/Characterization/Electrochemistry/Performance/Mechanism/Highlights/Limitations sections render structured data. | Reader Intelligence/Ask tabs and structured sections implemented; frontend tests exercise brief/field origin/status/confidence, evidence and verification actions. |
| 82 | PASS | Each evidenced field exposes Show evidence/source page. | Reader Intelligence/Ask tabs and structured sections implemented; frontend tests exercise brief/field origin/status/confidence, evidence and verification actions. |
| 83 | PASS | Field status/confidence are visible. | Reader Intelligence/Ask tabs and structured sections implemented; frontend tests exercise brief/field origin/status/confidence, evidence and verification actions. |
| 84 | PASS | Verification actions are available inline. | Reader Intelligence/Ask tabs and structured sections implemented; frontend tests exercise brief/field origin/status/confidence, evidence and verification actions. |
| 85 | PASS | Library shows parse/extraction/review state. | Work serialization returns parse/review state; Library shows chips and selected-work batch controls; Tasks displays per-paper state and provider context. |
| 86 | PASS | Batch action can be launched from selected Library Works. | Work serialization returns parse/review state; Library shows chips and selected-work batch controls; Tasks displays per-paper state and provider context. |
| 87 | PASS | Intelligence screen is lazy-loaded/code-split where practical. | Vite produces separate Intelligence, AISettings and Reader chunks; React.lazy/Suspense boundaries. |
| 88 | PASS | Ask Paper retrieval is paper-scoped by default. | FTS query constrains Work and document IDs. Cross-Work query test returns no matches. No web/other-paper adapter is invoked. |
| 89 | PASS | Retrieval uses parsed chunks/FTS and does not silently query the web. | FTS query constrains Work and document IDs. Cross-Work query test returns no matches. No web/other-paper adapter is invoked. |
| 90 | PASS | Answers contain clickable page citations. | Paper-scoped Ask integration/UI tests: citations/snippets, unsupported question fallback, no-evidence Knowledge rejection; questions/answers stored in SQLite. |
| 91 | PASS | Cited snippets are inspectable. | Paper-scoped Ask integration/UI tests: citations/snippets, unsupported question fallback, no-evidence Knowledge rejection; questions/answers stored in SQLite. |
| 92 | PASS | An unanswerable question can return Not found in this paper. | Paper-scoped Ask integration/UI tests: citations/snippets, unsupported question fallback, no-evidence Knowledge rejection; questions/answers stored in SQLite. |
| 93 | PASS | Saving an Ask Paper claim to Knowledge requires attached evidence. | Paper-scoped Ask integration/UI tests: citations/snippets, unsupported question fallback, no-evidence Knowledge rejection; questions/answers stored in SQLite. |
| 94 | PASS | Restart preserves saved paper questions/answers if persistence is enabled by design. | Paper-scoped Ask integration/UI tests: citations/snippets, unsupported question fallback, no-evidence Knowledge rejection; questions/answers stored in SQLite. |
| 95 | PASS | Structured paper extraction exports to JSON. | JSON/CSV integration tests retain field paths and pages. Export reads only extraction/run/anchor/decision entities; keys never reside in them. |
| 96 | PASS | Measurement/extraction data exports to CSV. | JSON/CSV integration tests retain field paths and pages. Export reads only extraction/run/anchor/decision entities; keys never reside in them. |
| 97 | PASS | Evidence page references survive export. | JSON/CSV integration tests retain field paths and pages. Export reads only extraction/run/anchor/decision entities; keys never reside in them. |
| 98 | PASS | Export does not include provider secrets. | JSON/CSV integration tests retain field paths and pages. Export reads only extraction/run/anchor/decision entities; keys never reside in them. |
| 99 | BLOCKED | On Windows, import/open one real text-based electrocatalysis paper and parse it. | BLOCKED: awaiting Product Owner Windows real-paper / real-provider walkthrough in docs/phase2b1-manual-acceptance.md. No waiver received. |
| 100 | BLOCKED | Run one real provider OR local-provider extraction under user-controlled credentials/configuration. | BLOCKED: awaiting Product Owner Windows real-paper / real-provider walkthrough in docs/phase2b1-manual-acceptance.md. No waiver received. |
| 101 | BLOCKED | Manually inspect at least 10 extracted fields across synthesis, electrochemistry and mechanism; source buttons must return to correct pages. | BLOCKED: awaiting Product Owner Windows real-paper / real-provider walkthrough in docs/phase2b1-manual-acceptance.md. No waiver received. |
| 102 | BLOCKED | Deliberately correct one field and confirm correction persists. | BLOCKED: awaiting Product Owner Windows real-paper / real-provider walkthrough in docs/phase2b1-manual-acceptance.md. No waiver received. |
| 103 | BLOCKED | Ask at least two paper-scoped questions and confirm citations point into the same paper. | BLOCKED: awaiting Product Owner Windows real-paper / real-provider walkthrough in docs/phase2b1-manual-acceptance.md. No waiver received. |
| 104 | BLOCKED | Run a small 3–5 paper batch and confirm one bad/unsupported item does not abort the others. | BLOCKED: awaiting Product Owner Windows real-paper / real-provider walkthrough in docs/phase2b1-manual-acceptance.md. No waiver received. |
| 105 | PASS | Windows CI passes backend tests. | Windows CI 38219956334 succeeded at c0a682e; final follow-up validation is linked in the PR. |
| 106 | PASS | Windows CI passes frontend tests. | Windows CI 38219956334 succeeded at c0a682e; final follow-up validation is linked in the PR. |
| 107 | PASS | Windows portable build succeeds. | Local build-windows.ps1 succeeds; frozen sidecar synthetic import/extract/Ask smoke passes. Windows CI 38219956334 also passed packaging and frozen smoke. |
| 108 | PASS | Build artifact is uploaded. | Windows CI 38219956334 succeeded at c0a682e; final follow-up validation is linked in the PR. |

## Known limits and manual review

- Items 99–104 await explicit user evidence. Mock extraction is intentionally conservative and is not a substitute for a real scientific model. No real PDF text has been sent to a cloud provider by the agent.
- Browser-control tooling was unavailable in this session. Real interface checks are delegated through the documented Windows walkthrough; automated component/geometry tests and frozen HTTP smoke are recorded separately.
- Parsing is heuristic; mixed scanned documents are marked Needs OCR. No OCR, automatic figure/table vision, semantic embeddings or cross-paper ranking is included. Table/figure captions are candidates, not interpreted data.
- Targeted extraction uses bounded relevant chunks per section. Long/complex papers may omit results; missing values remain unknown and require user review. Evidence matching confirms provenance/numbers/units, not the correctness of the paper or every paraphrased scientific claim.
- No RHE conversions/interpolations are computed. Model-proposed computations stay Needs review. Abstract mode suppresses detailed synthesis/electrochemistry/performance fields conservatively.
- Pause/cancel allows current paper requests to finish safely; completed results remain reusable. Retry resumes the same job. Runtime workers are bounded; job result metadata grows with selected IDs (maximum 1000, confirmation above 50).
- Migration tables follow the repository's Alembic model-metadata pattern. Backup export is the entire SQLite snapshot plus managed PDFs; OS keys are never part of it.
- All merge decisions remain with Product Owner. Open a review PR with this PARTIAL report; do not merge or claim full acceptance without manual evidence or explicit permitted waivers.
