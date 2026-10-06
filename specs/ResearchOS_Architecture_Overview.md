# ResearchOS architecture at a glance

Search adapters -> Canonicalization/Dedup -> Work DB -> Full-text acquisition -> PDF parser
-> Structured extraction -> Evidence store -> Library/Zotero -> Watch/Alerts -> Review Studio

Core rule: a Work is one canonical scholarly object. Source hits, PDFs, Zotero records,
annotations, extracted measurements and claims all reference that Work.

AI summaries are never the source of truth. Trusted metadata plus the user's PDF/full text and
explicit evidence provenance are the source of truth.
