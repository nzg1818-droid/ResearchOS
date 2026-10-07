# ResearchOS Integration Architecture

## Purpose
ResearchOS should become a research hub that reuses existing desktop software and online resources instead of reimplementing every tool.

Priority for external integration:

1. Official API
2. Supported local API / protocol / command-line interface
3. File exchange (RIS/BibTeX/CSV/XLSX/etc.)
4. OS-level open-with/deep-link
5. UI automation only as a last resort

Do not scrape or automate a UI when a stable official interface exists.

## Capability-oriented model
Not every integration supports every operation. Avoid one huge interface.

Define small protocols/capabilities such as:
- `HealthCapability`
- `SearchCapability`
- `ImportCapability`
- `ExportCapability`
- `SyncCapability`
- `OpenExternalCapability`
- `AttachmentCapability`

A provider advertises supported capabilities.

Example future providers:
- OpenAlex: Search, Import metadata, Open external
- Crossref: Search, Import metadata, Open external
- Zotero: Import, Export, Sync, Attachment, Open external
- Web of Science: Search, Import metadata, citation enrichment
- Semantic Scholar: Search, citation graph
- EndNote: file exchange first; API only if officially supported
- Origin: export/open data first
- Excel: export/open data
- VOSviewer: network-file export/open
- Stork: RIS/email interoperability unless a stable official API is available

## Security
Each integration declares permissions, for example:
- read metadata
- write metadata
- upload attachment
- launch external application
- delete remote data

Default rule: no delete/destructive permission in early versions.

Secrets:
- OS keyring only
- backend only
- never renderer localStorage
- never logs
- never backup bundles

## Phase 2A implementation boundary
Only implement the common infrastructure required by Zotero. Do not build connectors for other tools yet.

Recommended layout:

```text
backend/app/integrations/
  __init__.py
  capabilities.py
  registry.py
  zotero/
    base.py
    local.py
    web.py
    mapping.py
    sync.py
```

The registry should expose provider status/capabilities without leaking secrets.

## Future desktop-tool pattern
When ResearchOS later integrates Origin/Excel/VOSviewer/Word/EndNote, prefer:

ResearchOS structured data
→ export file or supported protocol
→ launch external app

rather than mouse/keyboard automation.

## Future network-resource pattern
ResearchOS query
→ multiple provider adapters
→ provider provenance
→ canonical Work merge
→ local structured database

This is the long-term path for WoS, Semantic Scholar, ORCID, PubMed/Europe PMC, arXiv, and institutional repositories.
