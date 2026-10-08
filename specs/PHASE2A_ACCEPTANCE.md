# ResearchOS Phase 2A Acceptance Gate

Phase 2A is not complete until every mandatory item below is evidenced.

## A. Regression gate
1. All Phase 1 backend tests pass.
2. All Phase 1 frontend tests pass.
3. Phase 1 search still uses real OpenAlex/Crossref production adapters.
4. Phase 1 PDF import, annotations, materials, and source backlinks still work.
5. Phase 1 Windows portable build still succeeds.

## B. Migration and portability
6. A real/synthetic Phase 1 database migrates to Phase 2A without data loss.
7. A pre-migration database backup is created automatically.
8. Managed attachment paths use portable relative storage semantics.
9. Copy the whole ResearchOS data folder to a different absolute path; existing PDFs still open.
10. Existing saved material backlinks still reopen the correct page/highlight after the move.
11. Corrupt/missing managed attachment detection works.

## C. Scale
12. PDF matching no longer performs a full corpus scan for common matching paths.
13. >=10,000 synthetic Works performance test passes within a documented target.
14. Search-run provenance is queryable and repeated searches do not create uncontrolled duplicate source-hit history.

## D. Reader UI v0.2
15. Permanent left global navigation is removed/replaced by top app navigation.
16. Reader left panel can open/close and resize.
17. Reader right panel can open/close and resize.
18. Panel widths/open state persist between sessions.
19. Focus mode hides global navigation and both panels while retaining document controls.
20. Zen/full-screen mode enters Electron full screen and exits safely with Esc.
21. Fit width works.
22. Fit page works.
23. Search inside PDF works and shows next/previous match.
24. Opening/closing panels does not lose current PDF page.
25. Existing annotation overlays remain aligned after zoom changes.
26. Knowledge → Open source still returns to exact page/highlight.
27. Command palette exposes the required common actions.
28. PDF-heavy Reader is code-split/lazy-loaded if practical; if not, document measured reason.

## E. Zotero security
29. Zotero integration never edits `zotero.sqlite`.
30. Secrets are stored only in OS keyring.
31. Automated security test confirms Zotero keys do not appear in SQLite, logs, backup archives, or renderer localStorage.
32. Backend owns authenticated Zotero calls.
33. Test connection and clear/revoke credential flows work.

## F. Zotero import
34. Mocked local API import works.
35. Mocked Web API import works.
36. DOI import matches an existing Work instead of duplicating.
37. Safe fallback matching without DOI works.
38. Conflicting DOI is never silently merged.
39. Tags, notes, collection membership, and attachment metadata import correctly.
40. Import summary reports created/matched/updated/skipped/conflict/error counts.

## G. Zotero export/sync
41. Push a new ResearchOS Work to mocked Zotero.
42. Choose destination Zotero collection.
43. Local-only update pushes safely.
44. Remote-only update pulls safely.
45. Simultaneous local+remote changes create a Conflict state.
46. Field-level conflict resolution persists.
47. DOI conflict requires explicit user resolution.
48. Zotero version/optimistic concurrency logic is used where supported.
49. Same PDF SHA-256 never creates duplicate managed bytes.

## H. Backup/restore/export
50. Backup bundle contains DB, managed attachments, and manifest.
51. Backup does not contain secrets.
52. Restore into a different directory reproduces Works, annotations, materials, and PDFs.
53. Backup manifest checksum verification works.
54. RIS export works.
55. BibTeX export works.
56. CSL-JSON export works.

## I. UI integration
57. Zotero is a top-level destination.
58. Zotero views include Connection, Import, Sync, Conflicts, Collection mappings.
59. Library clearly shows Zotero linked/unlinked and sync state.
60. Settings includes Storage & Backup and Integrations/Zotero.
61. Tasks remain accessible through top navigation and global progress indicator.

## J. Windows delivery
62. Backend automated suite passes in CI.
63. Frontend automated suite passes in CI.
64. Windows portable build succeeds in GitHub Actions.
65. Build artifact is uploaded.
66. Manual Windows smoke test confirms application launch.
67. Manual reader Focus/Zen behavior is verified.
68. Manual Zotero test uses a temporary/test library or collection, not destructive operations on the primary library.

## Completion decision

### PASS
- all mandatory items above pass
- zero critical regressions
- zero silent metadata-overwrite paths
- zero plaintext-secret findings

### PARTIAL
Any mandatory item lacks evidence or has a documented defect that does not threaten data integrity/security.

### FAIL
Any of:
- data loss during migration
- direct Zotero SQLite modification
- plaintext credential storage
- silent DOI conflict merge
- destructive sync overwrite
- source backlink regression
- Windows build failure

`PHASE2A_REPORT.md` must explicitly map each item 1–68 to PASS/FAIL/BLOCKED plus evidence.
