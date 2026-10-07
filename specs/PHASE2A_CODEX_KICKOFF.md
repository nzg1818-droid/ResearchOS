# Codex Kickoff — ResearchOS Phase 2A / v0.2

You are implementing ResearchOS Phase 2A on branch `feat/phase2a-zotero`.

## Read these files first, in this order
1. `ARCHITECTURE.md`
2. `PHASE1_REPORT.md`
3. `specs/PHASE2A_PRODUCT_SPEC_V2.md`
4. `specs/UI_V2_SPEC.md`
5. `specs/INTEGRATION_ARCHITECTURE.md`
6. `specs/PHASE2A_ACCEPTANCE.md`

These files are the authoritative product requirements. Do not spend tokens redesigning the product from scratch. Implement them.

## Execution rules
- Start from the existing `feat/phase2a-zotero` branch created from merged `main`.
- Run the Phase 1 tests first and record baseline results.
- Implement Phase 2A in vertical slices, not one giant rewrite.
- Preserve user data and Phase 1 behavior.
- Add Alembic migrations; never reset the DB to avoid migration work.
- Never edit `zotero.sqlite`.
- Never store secrets outside OS keyring.
- Use official Zotero interfaces only.
- Keep backend/provider logic separated from React UI.
- Do not implement Phase 2B/3 features.

## Suggested implementation order
1. Storage abstraction + relative attachment migration + pre-migration backup
2. Search provenance + scalable PDF matching + annotation context improvement
3. New top navigation + Reader left/right panels + Focus/Zen layout
4. PDF fit-width/fit-page/find + layout persistence + command palette
5. Zotero integration interfaces + secure settings + mocked fixtures
6. Zotero import and identity matching
7. Zotero push/export
8. Incremental sync + conflict UI
9. Backup/restore + diagnostics
10. RIS/BibTeX/CSL-JSON export
11. Full regression + Windows CI/package + manual acceptance

At the end create `PHASE2A_REPORT.md` mapping all 68 acceptance items in `specs/PHASE2A_ACCEPTANCE.md` to PASS/FAIL/BLOCKED with evidence.

Open a PR from `feat/phase2a-zotero` to `main`, but DO NOT MERGE IT. Product-owner review is required first.

When reporting completion, return only the repo/PR, latest commit SHA, test summary, Windows artifact/run instructions, manual acceptance status, and known limitations. Do not claim completion if a mandatory gate is unverified.
