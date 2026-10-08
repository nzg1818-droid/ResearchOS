# ResearchOS Phase 2A / v0.2 acceptance report

Status: **PARTIAL — mandatory live Zotero/manual gates remain open.** No Phase 2A PR has been opened or merged. No Phase 2B features are implemented.

Date: 2026-10-08 (Australia/Sydney). Repository: https://github.com/nzg1818-droid/ResearchOS . Branch: `feat/phase2a-zotero`.

The first published implementation is `5c379249557c857a4c9a505bd704e7e3849bf413`. Its [Windows CI run](https://github.com/nzg1818-droid/ResearchOS/actions/runs/37725097791) passed backend tests, frontend tests, Windows packaging and artifact upload. Follow-up fixes and this report are additional commits; the final reviewed head and matching CI evidence must be recorded before acceptance. The report does not claim the earlier CI run covers unpublished changes.

## Implementation and verification

Read `specs/PHASE2A_CODEX_KICKOFF.md` and its six referenced documents in the specified order. Started from the existing remote specification branch, descended from merged Phase 1. Baseline: 11 backend and 3 frontend tests passed before changes (`docs/phase2a-baseline.md`).

Slices implemented:

- Frozen Phase 1 migration schema; Alembic 0002 adds relative attachment references, indexed identity keys, bounded annotation context, search runs/snapshot relationships and integration state. SQLite backup runs before the 0001→0002 migration. Original PDFs are copied, never modified.
- Top navigation, responsive overflow, lazy Reader, independent panel controls/width persistence, Focus, native fullscreen IPC/Zen, fit controls, rotation, PDF text search, command palette, library selection/export and material filters.
- Typed capability boundary and official Local/Web v3 adapters. Local APIs without write capability report read-only. Backend owns authentication, OS keyring owns secrets, and versions protect remote writes. Import preview, identity matching, external attachment references, explicit managed copying, push, collection mapping and field conflict resolution are exposed in the UI.
- Verified SQLite/attachment backup, checksum validation, new-folder restore, diagnostics and RIS/BibTeX/CSL-JSON export.

Latest local regression: **34 backend tests passed**, **11 frontend tests passed**, TypeScript check passed. Commands:

```powershell
# backend/
../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
# repository root
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vitest/vitest.mjs run --pool=threads --configLoader native
./scripts/build-windows.ps1
```

The indexed regression seeds 10,000 Works, checks SQLite's identity index plan, rejects unfiltered Work SELECTs, and requires combined PDF/metadata matching below 3 seconds. Backup tests corrupt archive bytes and managed files, reject replacement destinations, restore into another directory, and compare PDF bytes plus annotation/material provenance.

Security tests place a canary credential in a mocked OS keyring and verify it is absent from SQLite, logs, ZIP entries and renderer localStorage. This tests the application boundary, not a substitute credential-store implementation. No code accesses `zotero.sqlite`. Clearing a connection removes the stored credential and disables it; remote Web-key revocation is explicitly delegated to Zotero account settings.

## Windows package and manual evidence

Portable ZIP: `release/ResearchOS-0.2.0-win-x64.zip`; checksum beside it in `.zip.sha256`. Extract the whole archive and run `ResearchOS-0.2.0-portable/ResearchOS.exe`. Python/Node are not required on the target machine. This is an unsigned portable build.

The first v0.2 package SHA-256 was `6bb708e859dd141601a270049e8ae63f41d7a90f2e3bdaa9374cbbbe8b051978`. Product Owner confirmed it opens and confirmed Windows Focus/Zen/Escape behavior. Subsequent revisions require their current checksum to be distinguished from this launch-tested package.

Detailed actual renderer checks and remaining native/Zotero steps: `docs/phase2a-manual-acceptance.md`. Real Zotero credentials and test collection are user-controlled; no destructive operations were performed on the main library.

## Acceptance matrix

PASS rows state their evidence boundary. BLOCKED means required evidence is absent, not an assumed pass.

| # | Result | Evidence |
|---|---|---|
| 1 | PASS | All 11 original backend tests retained in the 34-test run. |
| 2 | PASS | All 3 original frontend tests retained in the 11-test run. |
| 3 | PASS | Production OpenAlex/Crossref adapters unchanged; original shape/parameter tests pass. |
| 4 | PASS | Original import/persistence tests; actual PDF.js save and source backlink workflow. |
| 5 | PASS | v0.2 local Windows build and published implementation CI build. |
| 6 | PASS | Synthetic 0001 DB migrates with Work, File, Annotation and Material preserved. |
| 7 | PASS | Migration regression asserts automatic database backup exists. |
| 8 | PASS | Storage resolver and migrated `files/<sha256>.pdf` asserted. |
| 9 | PASS | Copied data root serves identical PDF after old managed PDF is removed. |
| 10 | PASS | Moved-root annotation IDs/pages and material file references preserved; same UI backlink route regression. |
| 11 | PASS | Diagnostics detects corrupted bytes and missing PDF. |
| 12 | PASS | Indexed PDF/title matching regression rejects corpus scans. |
| 13 | PASS | 10,000 Works, indexed query plan, documented <3 second target. |
| 14 | PASS | Three searches retain three runs but share one source snapshot. |
| 15 | PASS | Actual browser inspection: top bar, responsive destination menu, no permanent rail. |
| 16 | PASS | Reader interaction test toggles and resizes left panel. |
| 17 | PASS | Reader interaction test toggles right panel; bounded width control implemented. |
| 18 | PASS | Layout persistence/clamping test and saved state asserted. |
| 19 | PASS | Actual browser Focus/Escape plus interaction regression. |
| 20 | PASS | Product Owner confirmed native Zen fullscreen and Escape exit on 2026-10-08; IPC regression also passes. |
| 21 | PASS | Actual PDF.js Fit width rendered and adjusted zoom. |
| 22 | PASS | Actual PDF.js Fit page rendered and adjusted zoom. |
| 23 | PASS | Actual three-page PDF search plus next/previous interaction test. |
| 24 | PASS | Panel-toggle test retains page and render count; actual page 2 retained. |
| 25 | PASS | Actual focused overlay after zoom; rotation round-trip geometry test. |
| 26 | PASS | Actual Knowledge source action returns page 2/highlight; original frontend regression. |
| 27 | PASS | Command palette exposes navigation/import/panel/Focus/Zotero/backup actions in App. |
| 28 | PASS | Build produces separate Reader JS and PDF worker chunks; Reader uses React.lazy. |
| 29 | PASS | Official HTTP adapters only; no Zotero database path/query in integration implementation. |
| 30 | PASS | Keyring-only registry; non-secret connection schema; canary persistence test. |
| 31 | PASS | Canary scan of DB/logs/backup plus frontend localStorage test. |
| 32 | PASS | Renderer calls authenticated local backend; Zotero API key remains backend-only after entry. |
| 33 | BLOCKED | Mocked test/clear passes; real Windows keyring connection and revoke workflow pending. |
| 34 | PASS | Mocked Local API import test. |
| 35 | PASS | Mocked Web API import test. |
| 36 | PASS | Existing DOI matches one Work in parameterized test. |
| 37 | PASS | No-DOI title/author/year match test. |
| 38 | PASS | Conflicting DOI preserves local identity and records Conflict. |
| 39 | PASS | Tags, remote note origin, membership and attachment metadata asserted. |
| 40 | PASS | Summary shape and created/matched/skipped/conflict/updated paths covered; request-level errors returned explicitly. |
| 41 | PASS | Mocked new Work push test. |
| 42 | PASS | Mocked push asserts selected remote collection. |
| 43 | PASS | Local title change safely pushes with version precondition. |
| 44 | PASS | Remote-only sync and repeated-import pull tests. |
| 45 | PASS | Both-side title edits produce Conflict without overwrite. |
| 46 | PASS | Field choice resolves and persists In sync in round-trip test. |
| 47 | PASS | DOI change recorded as explicit conflict, retained until field choice. |
| 48 | PASS | PATCH version headers asserted; simulated race returns Conflict. |
| 49 | PASS | Repeated remote PDF copy retains one managed file/hash. |
| 50 | PASS | Backup/manifest test with DB and managed PDFs. |
| 51 | PASS | Canary absent from all backup entries; allow-listed archive contents. |
| 52 | PASS | Automated new-directory restore preserves PDF, page and material. Native reopen pending separately. |
| 53 | PASS | Corrupt archive rejected before destination creation. |
| 54 | PASS | RIS exports tested for single/selected/collection/library. |
| 55 | PASS | BibTeX exports tested, including escaped delimiters. |
| 56 | PASS | CSL-JSON exports parsed and DOI checked. |
| 57 | PASS | Top destination present in App and actual browser navigation. |
| 58 | PASS | Connection/Import/Sync/Conflicts/Collection mappings components implemented. |
| 59 | PASS | Library displays item ID, linked status and managed/external PDF state. |
| 60 | PASS | Storage & Backup and Integrations/Zotero settings implemented. |
| 61 | PASS | Top Tasks navigation and running count maintained from job polling. |
| 62 | PASS | CI 37725097791 backend step; follow-up head needs matching CI. |
| 63 | PASS | CI 37725097791 frontend step; follow-up head needs matching CI. |
| 64 | PASS | CI 37725097791 Windows build; follow-up head needs matching CI. |
| 65 | PASS | CI 37725097791 upload-artifact step succeeded. |
| 66 | PASS | Product Owner explicitly confirmed v0.2 application opens. |
| 67 | PASS | Product Owner explicitly confirmed Windows Focus, Zen and Escape behavior on 2026-10-08. |
| 68 | BLOCKED | Web API + dedicated test collection selected; actual import/push/conflict/PDF test pending. |

## Known limitations and outstanding review

- Real Zotero Web writes/PDF upload and native restore-reopen must still be verified. Mocked results are not live acceptance.
- Collections remain flat locally; remote parent keys are preserved and shown. Mirror affects mapped membership only and never deletes remote items.
- Bibliographic note comparison currently maps ResearchOS paper notes to Zotero `extra`; child notes are separately retained with origin. Optional named ResearchOS notes are version-checked; externally changed named notes are refused until reviewed. This distinction must be assessed during real Zotero acceptance.
- Remote deletion is not propagated as local deletion. There is no destructive sync capability.
- Local write support depends on the official server capability; legacy Local API versions remain read-only. Changing a local server identity is rejected rather than reusing unrelated versions.
- Reader zoom is persisted; fit mode is recalculated on selection. Image-only PDFs need an existing text layer; OCR is deferred.
- Request-level import failures abort the current import transaction and return an error; partial per-item recovery is not implemented. Full-library preview can be slow because child metadata is fetched for each selected parent.
- One upstream Starlette/httpx deprecation warning remains. Main renderer chunk exceeds Vite's advisory threshold; PDF-heavy code is nevertheless separately loaded.

Do not mark the phase complete or merge before the remaining evidence and any resulting fixes have been reviewed.
