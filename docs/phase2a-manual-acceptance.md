# Phase 2A manual acceptance

Use a dedicated Zotero test collection. Do not run acceptance against the whole personal library. Credentials are entered only in ResearchOS → Zotero → Connection.

## Recorded evidence (2026-10-08, Australia/Sydney)

- Product Owner confirmed the v0.2 portable application opens: “可以打开”. This confirms launch. In a subsequent answer “是”, the Product Owner also confirmed Focus hides navigation/panels, Zen enters native fullscreen, and Escape exits.
- Actual PDF.js renderer, exercised through the in-app browser against the frozen Windows sidecar: imported a synthetic three-page PDF; opened Library → Read PDF; Fit page and Fit width rendered the page; Find “Catalyst” returned three matches; Next match opened page 2; toggling the left panel retained page 2.
- Focus hid navigation and both panels; Escape restored them in the browser renderer.
- Selected PDF text on page 2, entered “Phase 2A source backlink check”, and saved evidence through the UI. Knowledge → Open source returned to page 2 with the focused highlight; increasing zoom retained its alignment.
- An initial transient “Failed to fetch” message occurred during the development-server/sidecar transition. Reopening the Reader succeeded without that error. Authenticated PDF, annotations, Work and material endpoints returned 200.
- Native Electron fullscreen is confirmed by the Product Owner.
- Product Owner subsequently configured Web API credentials and confirmed Test connection succeeds. No credential was shared in chat.
- Product Owner confirmed first import completed, second import produced no duplicates, and neither import reported errors.
- Product Owner confirmed the pushed parent appears in the target collection. Opening its PDF failed because attachment bytes were missing; Zotero cloud storage is full. Product Owner explicitly skipped PDF cloud-transfer acceptance. This is not a successful PDF upload.
- Product Owner explicitly skipped the live conflict walkthrough. Automated field-conflict coverage remains separate evidence.
- In response to the backup ZIP → validation → new-folder restore → restart → PDF/material source check, Product Owner confirmed “一切正常”. This completes the requested native backup/restore walkthrough.
- A subsequent upload-status fix persists incomplete transfers as Error, retains the error across metadata sync, verifies remote checksum, and supports retry without duplicate parents/attachments. Its quota/retry/upload checks pass automatically; a new live upload remains unverified.

## Walkthrough and disposition

1. Open a PDF. Enter Focus and exit it. Enter Zen: confirm the window enters native fullscreen, the toolbar hides after inactivity, mouse movement reveals it, and Escape restores the normal window.
2. Zotero → Connection: select Web, enter the correct user/group library ID and key, save, then Test connection. Do not send the key in chat. Use a key with only the permissions needed for the test library.
3. Zotero → Import: load collections, select the test collection, preview and import. Repeat the import. Confirm existing DOI Works do not duplicate, tags/collection/note origin/attachment references are visible, and the summary is reasonable.
4. In Library, create a synthetic test paper and attach a lawful test PDF. Select it, choose Push selected to Zotero, load the destination test collection, enable PDF upload, then push. Confirm the new parent item and PDF appear in that collection in Zotero.
5. Change the linked title locally and remotely before synchronizing. Confirm Conflict appears, both values remain visible, and field-level resolution returns it to In sync without overwriting the unchosen version silently.
6. Settings → Storage & Backup: create a verified ZIP, restore into a new absolute folder, restart with the restored library, and reopen the same PDF and material source page.

Disposition: step 1 Focus/Zen/Escape confirmed (toolbar inactivity details were not separately attested); steps 2 and 3 connection/import/dedup confirmed; step 4 parent destination confirmed, PDF transfer SKIPPED due to quota; step 5 SKIPPED at Product Owner request; step 6 confirmed. Granular tag/note-origin checks rely on automated evidence. Open a review PR with these exceptions and retain PARTIAL status; never merge before formal Product Owner approval.
