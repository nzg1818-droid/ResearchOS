# ResearchOS Phase 2B1 Acceptance Gate

Phase 2B1 is complete only when all mandatory items are evidenced and no critical integrity/privacy regression exists.

## A. Regression and carry-forward
1. All Phase 2A backend tests still pass.
2. All Phase 2A frontend tests still pass.
3. Windows portable build still succeeds.
4. Search/Library/Reader/Knowledge/Zotero/backup remain functional.
5. Zotero Web key introspection can identify/validate personal user ID and permissions without putting the key in URLs/logs/storage.
6. Local Zotero 401 presents a clear re-authorization path.
7. Existing MUI out-of-range warning is removed.

## B. Document parsing
8. Text PDF creates a paper_document record.
9. All PDF pages are represented with correct page numbers.
10. Text blocks retain normalized bbox coordinates.
11. Stable chunks are produced in reading order.
12. Chunks retain page and section/heading provenance.
13. Reparse of identical file/parser version is idempotent or cache-reused.
14. Text hash changes when source text changes.
15. Image-only/scanned PDF is marked Needs OCR rather than falsely Parsed.
16. Parser failure is isolated and user-visible.
17. Parsing runs off the UI thread/background task path.

## C. Extraction model
18. Strict versioned extraction schema exists.
19. Metadata extraction level works.
20. Abstract extraction level works and is visibly marked abstract-only.
21. Full-text extraction level works.
22. Full-text verified state is distinct from ordinary full-text extraction.
23. Materials are represented structurally, not prose-only.
24. Synthesis steps are ordered and structured.
25. Characterization records distinguish ex-situ/in-situ/operando when reported.
26. Electrochemical conditions are structured.
27. Performance measurements are row-oriented structured records.
28. Mechanism claims distinguish source_reported from ai_interpretation.
29. Unknown fields remain unknown/null rather than being filled speculatively.
30. Schema-invalid model output is rejected/repaired through a bounded path and never silently persisted as valid.

## D. Evidence contract
31. Every persisted numeric performance value has at least one evidence anchor or explicit Needs review status.
32. Evidence anchor has Work/file/page/snippet provenance.
33. Evidence anchor page exists.
34. Evidence snippet can be matched back to parsed source text.
35. Evidence bbox is stored where parser coordinates permit it.
36. Clicking evidence opens correct PDF page.
37. Evidence focus remains aligned after Reader zoom.
38. Numeric evidence validator catches a deliberately hallucinated/mismatched value.
39. Unit incompatibility produces Needs review instead of silent acceptance.
40. source_reported/app_computed/ai_interpretation are visibly distinct in UI and data.

## E. Human verification
41. User can Accept an extracted field.
42. User can Edit an extracted field.
43. User can Reject an extracted field.
44. Original extraction remains auditable after correction.
45. Verification decision stores timestamp and field path.
46. User verified/corrected status persists after restart.
47. Verified field can be saved to Knowledge with source evidence.

## F. AI provider and security
48. Typed provider interface exists.
49. Mock provider drives CI deterministically.
50. OpenAI-compatible configurable provider path exists.
51. Ollama/loopback local provider path exists.
52. App works without any AI provider configured.
53. Provider secrets are stored in OS keyring only.
54. Canary provider secret is absent from SQLite/logs/backups/renderer localStorage.
55. Remote endpoint validation requires HTTPS except loopback-local providers.
56. Test connection reports provider/model status without exposing secret.
57. Cloud-vs-local provider is explicit in UI.
58. Remote/cloud extraction requires explicit user consent before PDF-derived text is sent.
59. No newly imported PDF triggers cloud AI automatically.

## G. Cache and jobs
60. AI run records provider/model/prompt/schema/source hashes.
61. Identical successful extraction is cache-reused by default.
62. User can force re-run.
63. Prompt version change invalidates the relevant cache key.
64. Schema version change invalidates the relevant cache key.
65. Batch processing isolates per-paper failures.
66. Batch processing supports cancel or pause/resume/retry semantics consistent with the existing task architecture.
67. Interrupted batch can resume without duplicating completed extractions.
68. 50-paper synthetic batch is memory-bounded and does not crash.

## H. Scientific validity
69. Unknown iR correction remains unknown.
70. Unknown normalization basis remains unknown.
71. RHE conversion is not performed without sufficient inputs.
72. Any app-computed conversion records formula/inputs and status.
73. Precatalyst composition is not automatically asserted as the working-state active phase.
74. UOR current alone does not produce a claimed product distribution.
75. EGOR/HMFOR product metrics preserve FE/selectivity/yield context when reported.
76. Abstract-only mode does not fabricate synthesis recipes.
77. Ex-situ-only mechanism evidence is labeled as such.

## I. Intelligence UI
78. Reader has an Intelligence tab/panel.
79. Reader has an Ask Paper tab/panel.
80. One-minute brief renders from the latest extraction.
81. Materials/Synthesis/Characterization/Electrochemistry/Performance/Mechanism/Highlights/Limitations sections render structured data.
82. Each evidenced field exposes Show evidence/source page.
83. Field status/confidence are visible.
84. Verification actions are available inline.
85. Library shows parse/extraction/review state.
86. Batch action can be launched from selected Library Works.
87. Intelligence screen is lazy-loaded/code-split where practical.

## J. Ask Paper
88. Ask Paper retrieval is paper-scoped by default.
89. Retrieval uses parsed chunks/FTS and does not silently query the web.
90. Answers contain clickable page citations.
91. Cited snippets are inspectable.
92. An unanswerable question can return Not found in this paper.
93. Saving an Ask Paper claim to Knowledge requires attached evidence.
94. Restart preserves saved paper questions/answers if persistence is enabled by design.

## K. Export
95. Structured paper extraction exports to JSON.
96. Measurement/extraction data exports to CSV.
97. Evidence page references survive export.
98. Export does not include provider secrets.

## L. Manual acceptance
99. On Windows, import/open one real text-based electrocatalysis paper and parse it.
100. Run one real provider OR local-provider extraction under user-controlled credentials/configuration.
101. Manually inspect at least 10 extracted fields across synthesis, electrochemistry and mechanism; source buttons must return to correct pages.
102. Deliberately correct one field and confirm correction persists.
103. Ask at least two paper-scoped questions and confirm citations point into the same paper.
104. Run a small 3–5 paper batch and confirm one bad/unsupported item does not abort the others.
105. Windows CI passes backend tests.
106. Windows CI passes frontend tests.
107. Windows portable build succeeds.
108. Build artifact is uploaded.

## Decision rules

### PASS
- All mandatory items 1–108 PASS, or an external-service-only manual item is explicitly waived by Product Owner with strong automated evidence.
- Zero data-loss defects.
- Zero plaintext-secret defects.
- Zero silent evidence/metadata overwrite defects.
- Zero uncited numeric values presented as verified.

### PARTIAL
- Missing manual evidence or noncritical defect with integrity/privacy preserved.

### FAIL
Any of:
- source evidence lost or fabricated
- cloud PDF text sent without consent
- API key/secret persisted in plaintext
- schema migration loses Phase 2A data
- evidence link opens wrong paper/page systematically
- AI hallucinated numeric value becomes verified without evidence
- Phase 2A regression in Zotero/backup/source backlinks
- Windows build failure

`PHASE2B1_REPORT.md` must map every item 1–108 to PASS/FAIL/BLOCKED plus exact evidence.