---
status: partial
phase: 03-content-pages-ai-summary
source: [03-VERIFICATION.md]
started: 2026-04-26T00:00:00Z
updated: 2026-04-26T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. AI Summary 30-second wall-clock budget (Success Criterion #4)
expected: Run `uvicorn app_v2.main:app --host 0.0.0.0 --port 8000` with real Ollama (`ollama serve` + `ollama pull llama3.1`), open `/platforms/<an_existing_pid>` in a browser, click AI Summary. Spinner is visible immediately; summary card swaps in within 30 seconds (cold start may be slower; second click should be near-instant from cache).
result: [pending]

### 2. Visual layout — Dashboard panel + AI button gradient
expected: Open `/platforms/<pid>` and `/`. AI Summary button shows violet gradient (.ai-btn — `linear-gradient(135deg, #f3eeff, #e8eeff)`); panel mini-card rounded corners 22px radius; markdown-content typography matches UI-SPEC §7.
result: [pending]

### 3. HTMX swap behavior — error + retry interaction
expected: Stop Ollama (or set `endpoint` to a deliberately wrong URL); click AI Summary on a platform with content. Amber alert appears in the per-row summary slot (NOT in any global error container); Retry button is functional.
result: [pending]

### 4. Save → refresh persistence (Success Criterion #2 last clause)
expected: Save markdown content for a platform; refresh the browser tab. Saved content persists and renders identically.
result: [pending]

### 5. Delete confirmation copy
expected: Click Delete on a platform with content. Browser-native confirm() dialog shows verbatim "Delete content page for {PLATFORM_ID}? This cannot be undone."
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
