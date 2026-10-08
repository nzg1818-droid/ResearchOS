# Phase 2A baseline

2026-10-08: checked out the existing remote `feat/phase2a-zotero` at `74faa4e` (specification commit), descended from merged Phase 1 main `435bf0c`.

Read kickoff, then ARCHITECTURE, PHASE1_REPORT, PRODUCT_SPEC_V2, UI_V2_SPEC, INTEGRATION_ARCHITECTURE and ACCEPTANCE in that order.

Before applying implementation changes:

- `../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` from backend: **11 passed**, one upstream Starlette deprecation warning.
- `node node_modules/vitest/vitest.mjs run --pool=threads --configLoader native`: **3 passed**.

The previous unfinished implementation was preserved in Git stash `phase2a-pre-v2-spec-work` before fast-forwarding to the specification branch. Compatible storage/matching changes were then reapplied for slice-by-slice verification.

Product Owner selected Zotero Web API with a dedicated test collection for manual acceptance. Credentials must be entered in the application's secure settings, never in chat or repository files.
