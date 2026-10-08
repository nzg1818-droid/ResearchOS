# ResearchOS Phase 2B1 — Codex Kickoff

You are implementing Phase 2B1 on the existing repository.

## Branch
Use the existing branch:
`feat/phase2b1-paper-intelligence`

It was created from merged Phase 2A `main` after formal Product Owner acceptance.

## Authoritative documents
Read in this order before editing code:
1. `specs/PHASE2B1_PRODUCT_SPEC.md`
2. `specs/PHASE2B1_ACCEPTANCE.md`
3. `ARCHITECTURE.md`
4. `specs/INTEGRATION_ARCHITECTURE.md`
5. existing Phase 2A report/specs only when needed for compatibility

Do not redesign the product and do not expand scope beyond the specification.

## Execution order
Implement as vertical slices, running regression tests after each:

1. Carry-forward Phase 2A polish (Zotero key introspection/re-auth UI warning cleanup).
2. Alembic/data model for parsed documents, chunks, extraction/evidence/verification/AI runs.
3. Local PDF parser + stable chunking + Needs OCR detection.
4. Provider abstraction + Mock provider + security/privacy settings.
5. Versioned extraction schema and prompt templates.
6. Evidence linking + deterministic evidence validators.
7. Reader Intelligence UI + evidence jump + verification actions.
8. Ask Paper with paper-scoped FTS retrieval and page citations.
9. Batch parsing/extraction jobs + caching/restart behavior.
10. JSON/CSV export.
11. Full automated acceptance suite, Windows build and manual-evidence guide.

## Nonnegotiable rules
- Do not send PDF text to any cloud provider without explicit user action/consent.
- Never store provider keys in SQLite, logs, backups or renderer localStorage.
- Never persist a numeric performance value as evidenced unless a valid source anchor exists; otherwise mark Needs review.
- Never fabricate missing fields.
- Do not request or store chain-of-thought.
- Do not break Phase 2A Zotero, backup/restore, PDF annotations or Knowledge backlinks.
- Do not implement Phase 2B2/3 features (cross-paper ranking, Watch, Review Studio, citation-network analytics, OCR).

## Tests
Start by running the complete current backend/frontend suites and record the baseline.
Use deterministic provider mocks in CI; CI must not require a real API key.
Add fixtures covering an electrocatalysis paper-like PDF, numeric evidence mismatch, abstract-only mode, scanned/no-text PDF, provider failures and batch restart.

## Delivery
At completion:
- create `PHASE2B1_REPORT.md`
- map all 108 acceptance items to PASS/FAIL/BLOCKED
- include exact test commands/results
- include migration notes
- include security/privacy evidence
- include Windows CI run and artifact
- document any manual acceptance steps still requiring the user
- open a Phase 2B1 PR to `main`
- DO NOT merge it

When implementing, write working code, run tests, fix failures, and keep commits logically separated. Do not return only sample snippets or a plan.