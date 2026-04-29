---
status: partial
phase: 06-ask-tab-port
source: [06-VERIFICATION.md]
started: 2026-04-29T09:15:00Z
updated: 2026-04-29T09:15:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. First-turn answer render — Load `/ask` and submit a question
expected: Result table with LLM summary and collapsed SQL block appear in `#answer-zone` via HTMX swap; no full page reload
result: [pending]

### 2. Two-turn confirmation flow — trigger ClarificationNeeded then confirm
expected: Confirmation panel appears with candidate params pre-checked; after clicking "Run Query ▸" the confirmed params route to the second turn and return an answer fragment
result: [pending]

### 3. LLM backend cookie persistence
expected: Switch dropdown from Ollama to OpenAI; refresh page; dropdown label updates to "LLM: OpenAI ▾"; cookie `pbm2_llm=openai-prod` visible in DevTools; AI Summary on Overview also uses OpenAI
result: [pending]

### 4. Starter chip no-auto-submit
expected: Click any starter-prompt chip → textarea fills with chip text; form does NOT submit automatically; only manual Run click fires a network request
result: [pending]

### 5. Abort banner with verbatim v1.0 copy
expected: Submit a vague question that exhausts the 5-step agent cap; red banner appears with exact copy: "Agent stopped: reached the 5-step limit. Try rephrasing your question with more specific parameters."
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
