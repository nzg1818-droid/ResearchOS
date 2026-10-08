# ResearchOS v0.2 UI/UX Specification

## Goal
Redesign ResearchOS around long-form paper reading. The PDF must be able to occupy essentially the whole window, while navigation, evidence capture, metadata, and integrations remain one click away.

The current always-visible left navigation is replaced by a compact top application bar plus independently collapsible left/right reader panels.

## 1. Global layout

### Top application bar
Persistent outside Focus/Zen mode. Height target: 48–56 px.

Left-to-right:
- ResearchOS logo/home
- Search
- Library
- Reader
- Knowledge
- Zotero
- Tasks
- Settings
- flexible spacer
- active task indicator
- connection/status indicator
- command palette button

Rules:
- No permanent full-height navigation rail in normal app mode.
- On narrow windows, top destinations collapse into a single overflow/menu button.
- Current section remains visually clear without consuming large vertical space.

### Content area
Every non-reader page uses the full width under the top bar. Search and Library may use optional filter drawers, but they must be collapsible.

## 2. Reader workspace

Reader is the primary workspace and must support four layout states:

1. **Standard**: PDF + optional left panel + optional right panel.
2. **Wide reading**: PDF + one side panel.
3. **Focus**: PDF canvas fills all space below compact document toolbar; both side panels hidden.
4. **Zen/full-screen**: application chrome and side panels hidden; PDF and a minimal auto-revealing document toolbar remain.

Remember the user's last state per device.

### Reader top document toolbar
A second compact toolbar appears directly above the PDF in Reader mode.

Required controls:
- Back to previous context
- Paper title (truncated with tooltip)
- previous/next page
- page number / total pages
- zoom out/in
- zoom percentage
- Fit width
- Fit page
- rotate
- search inside PDF
- highlight mode/status
- toggle left panel
- toggle right panel
- Focus mode
- Full screen/Zen mode

Keyboard shortcuts should exist where practical and be documented.

### Left reader panel — collapsible/resizable
Tabs:
- Outline
- Thumbnails
- Find in PDF

Behavior:
- width resizable, recommended 220–420 px
- remembers width and open/closed state
- closing it must not resize PDF repeatedly during animation

### Right reader panel — collapsible/resizable
Tabs:
- Evidence
- Notes
- Metadata
- Materials
- Zotero (when linked)

Evidence tab:
- current selection
- note
- tags
- Save highlight
- Save as evidence
- Save as writing material

Notes tab:
- paper-level note
- annotation list
- quick tag editing

Metadata tab:
- title, authors, journal, year, DOI
- source providers
- OA status
- attachment state

Materials tab:
- evidence/writing materials from current paper
- click jumps to page/highlight

Zotero tab:
- linked/unlinked
- remote item key/status
- sync status
- push/sync/open actions

## 3. Full-screen reading requirements

A reader must be able to read a paper with maximum vertical/horizontal space.

### Focus mode
- hide global top app bar
- hide both side panels
- keep compact document toolbar
- one action restores previous layout

### Zen mode
- enter Electron full-screen
- hide global app bar and panels
- document toolbar auto-hides after inactivity and reappears on mouse movement/top-edge hover or keyboard shortcut
- Esc exits Zen mode
- state is not persisted across application restarts if that could trap the user

## 4. PDF behavior improvements

Required for v0.2:
- smooth page-to-page navigation
- Fit width and Fit page
- persistent zoom preference
- PDF text search with result count and next/previous result
- preserve current page when panels open/close
- annotation overlay remains aligned at every zoom level
- source backlink from Knowledge still opens exact page/highlight

Do not add OCR in Phase 2A.

## 5. Search UI v0.2

Top bar navigation opens Search.

Layout:
- compact search query bar at top
- mode selector: Keyword / Exact title / Author / DOI
- date controls
- source chips: OpenAlex / Crossref (later extensible)
- optional collapsible Filters drawer
- sortable results area

Keep Phase 1 semantics unchanged. Do not implement WoS/Semantic Scholar yet in Phase 2A.

## 6. Library UI v0.2

Use a desktop research-manager layout:
- optional collapsible collection/filter drawer on left
- central paper table/list
- optional right details drawer

The user can hide both drawers for a wide table.

Important visible fields:
- title
- first authors
- year
- journal
- DOI
- reading status
- starred
- PDF status
- Zotero sync state (Phase 2A)

## 7. Knowledge UI v0.2

Material cards/table should support:
- type: Highlight / Evidence / Writing
- source paper
- page
- tags
- note
- selected text preview
- Open source action
- filter by type/tag/paper

Clicking source always returns to the Reader with exact page/highlight.

## 8. Zotero UI

Add top-level Zotero destination with sub-tabs:
- Connection
- Import
- Sync
- Conflicts
- Collection mappings

Sync status terminology:
- Not linked
- In sync
- Local changes
- Remote changes
- Conflict
- Error

Never hide conflicts behind automatic overwrite.

## 9. Tasks and Settings

Tasks should be a top-level destination but also expose a compact global progress indicator in the top app bar.

Settings sections:
- General
- Storage & Backup
- Integrations
- Zotero
- Appearance

Appearance should at minimum prepare the structure for theme/density settings; do not spend significant Phase 2A effort on decorative themes.

## 10. Command palette

Add a lightweight command palette (e.g. Ctrl/Cmd+K) for frequent actions:
- Search literature
- Open Library
- Import PDFs
- Import folder
- Open Reader
- Toggle left reader panel
- Toggle right reader panel
- Focus mode
- Zotero sync
- Backup library

This reduces dependence on fixed navigation and supports keyboard-first research workflows.

## 11. Layout persistence

Persist non-sensitive UI preferences locally:
- panel open/closed state
- panel widths
- reader zoom
- last non-Zen reader mode
- Library drawer state

Do not persist credentials or API tokens in renderer storage.

## 12. Accessibility/interaction

- all icon-only buttons require accessible labels/tooltips
- keyboard focus must be visible
- essential actions cannot depend only on hover
- Esc closes transient panels/dialogs/Zen mode appropriately
- resizing must not make controls unreachable

## 13. Performance constraints

- avoid rerendering the full PDF when merely toggling a side panel
- lazy-load Reader/PDF-heavy code where practical
- v0.1 Vite warning showed a large PDF-enabled bundle; v0.2 should code-split PDF Reader if practical without destabilizing the build

## 14. Explicitly deferred

Not Phase 2A:
- AI assistant panel
- OCR
- semantic paper chat
- electrocatalysis extraction dashboard
- citation network visualization
- WoS/Scopus search UI

Reserve right-panel architecture so these can be added later without another layout rewrite.
