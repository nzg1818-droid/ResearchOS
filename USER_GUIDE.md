# ResearchOS Phase 1 user guide

## Discover and collect

1. Open Search. Choose keyword, exact title, author or DOI. Set a publication-date range or clear both date fields for all years.
2. Search queries both OpenAlex and Crossref. Tasks shows individual source counts and errors. Partial failures are clearly reported. Results retain source provenance and deduplicate by DOI, identifiers, then title/first-author/year.
3. Save a paper to Library. Open DOI or Open publisher launches your browser. Find OA copy lists only locations marked open access by OpenAlex; a link is not a guarantee the host is currently reachable.
4. Download a PDF through lawful browser access. Attach PDF associates it with the chosen paper. Import PDFs/Import folder in Library identifies metadata where possible, matches existing papers, and copies the file into managed storage. SHA-256 prevents importing the same bytes twice.

Provider metadata can be incomplete or incorrect. Unknown fields remain unknown. In particular, similarly titled editions can have different DOIs/dates; source records and conflicts are preserved rather than pretending these are identical. Check the selected paper before explicitly attaching a PDF.

## Organize the library

- Star a paper using its star button.
- Details & notes edits reading status, tags and notes. Save details persists them.
- Create collections in Library, then use their chips in Details & notes to add/remove a paper.
- Search local titles and notes through SQLite FTS5.
- Remove from Library hides membership, preserving annotations and attached sources. It does not delete the original PDF or the managed copy.

## Read, highlight and save materials

1. Choose Read PDF. Use Previous/Next, Page or Zoom. Horizontal scrolling is available at large zoom settings; the last zoom is remembered.
2. Drag across a sentence. Enter an annotation note and optional comma-separated tags.
3. Save highlight stores the mark and note. Save as evidence or Save as writing material additionally creates a material-bank entry.
4. Knowledge lists saved materials with title, DOI when available, authors/year, selected text, note and tags. Open source returns to the original file/page and locates the saved highlight.

The app stores normalized annotation coordinates, context from the current page, managed file reference/hash and creation timestamp. All are local and survive restart. Image-only/scanned PDFs can be read but need an existing text layer for text selection; OCR is not included in Phase 1.

## Tasks, errors and recovery

Search/import continue in the background. Tasks shows queued/running/completed/partial/failed/interrupted states. Retry reuses the stored input; repeated imports remain idempotent. Damaged PDFs are reported per file while other files continue importing. API throttling and temporary server failures receive bounded retry/backoff. Source authentication failures are visible.

## Settings and backup

An optional OpenAlex key can raise provider usage allowances. Save it in Settings; it is stored in Windows Credential Manager. Do not put secrets into notes, repository files or `.env`. Institutional passwords are never requested.

Settings displays the data folder. Exit the app, then copy the entire folder (including PDFs and database) for backup. Debug logs rotate locally. To restore, close the app and restore the folder before relaunching.

Phase 2 extraction, Zotero, semantic search and dashboards are not available in this version.
