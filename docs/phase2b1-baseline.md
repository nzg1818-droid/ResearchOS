# Phase 2B1 baseline

Branch: feat/phase2b1-paper-intelligence, existing remote specification branch from merged Phase 2A main.
Read kickoff, product specification, acceptance gate, ARCHITECTURE.md and integration architecture in order.

Before edits: backend 36 passed (one upstream Starlette/httpx deprecation warning); frontend 11 passed.
Commands: `../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` in backend; `node node_modules/vitest/vitest.mjs run --pool=threads --configLoader native` at root.
