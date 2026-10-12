# Phase 2B1 Windows manual acceptance — pending Product Owner evidence

Extract the entire `ResearchOS-0.3.0-win-x64.zip` into a normal directory and run `ResearchOS-0.3.0-portable/ResearchOS.exe`. This unsigned portable package requires no Python/Node installation. Preserve a backup of the accepted library before upgrading. Schema 0003 migration automatically backs up an existing 0002 DB.

1. **99** Import/open one real text-based electrocatalysis PDF. Open Intelligence, select Parse documents and Start. Confirm Parsed, reasonable page count and responsive Reader. A scanned test file should show Needs OCR.
2. **100** Settings → AI: configure a real HTTPS-compatible provider or loopback Ollama model using credentials entered only in the application. Test connection, select it, and run full-text extraction. Cloud mode must show provider/model/input estimate and require the consent checkbox. Do not send keys in chat.
3. **101** Inspect at least 10 populated fields across synthesis, electrochemistry and mechanism. For each, use Show evidence and confirm the correct paper/page/snippet. Change zoom and check highlight alignment. Treat confidence and Evidence matched as review aids, not scientific proof.
4. **102** Correct one value to the source-supported value, save with a note, restart and confirm User corrected persists. Check the original extraction remains available in JSON export/decision history. Reject a second unsupported field if present.
5. **103** Ask two questions about this paper. Inspect cited snippets and page links. Ask one unrelated question and confirm insufficient evidence is reported. Save an evidenced answer/verified field to Knowledge and reopen its source.
6. **104** Select 3–5 papers including one scanned/unsupported item. Run a batch. Confirm good papers complete while the bad one reports its own error. Pause/resume and restart/retry; completed extractions must not duplicate. Reconfirm cloud consent after resume.

Also check Phase 2A navigation, Zotero Test connection/import and a backup/new-folder restore. Avoid destructive changes to personal Zotero data.

Automated evidence: synthetic PDF parser; strict schema/mismatch checks; mocked HTTP providers; isolated frozen Windows sidecar smoke; 50-paper batch. These do not substitute for steps 99–104. No Phase 2B1 manual pass or waiver has yet been received.
