---
status: partial
phase: 02-nl-agent-layer
source:
  - 02-VERIFICATION.md
started: 2026-04-23
updated: 2026-04-23
---

## Current Test

[awaiting human testing — autonomous run continued to milestone lifecycle without live validation]

## Tests

### 1. Ask page happy path
expected: `streamlit run streamlit_app.py`; navigate to Ask; type a clear question ("Show all params for platform X"); agent returns result table + plain-text summary; SQL visible in collapsed expander with Regenerate button; history entry recorded.
result: [pending]

### 2. NL-05 two-stage confirmation
expected: Type a vague question ("Tell me about WriteProt"); agent returns ClarificationNeeded with candidate (InfoCategory, Item) pairs; multiselect pre-checks all candidates; click Run Query; answer zone renders with confirmed params injected into second-turn prompt.
result: [pending]

### 3. OpenAI sensitivity warning (NL-10)
expected: Switch sidebar LLM to an OpenAI entry; first navigation to Ask page shows dismissible warning banner "You're about to send UFS parameter data to OpenAI's servers. Switch to Ollama in the sidebar for local processing."; Dismiss closes it; browser refresh re-shows it.
result: [pending]

### 4. Backend switch takes effect
expected: Run a query on Ollama; switch sidebar to OpenAI; run another query; agent call actually uses OpenAI API (confirm via logs or API dashboard); no stale cached agent.
result: [pending]

### 5. Step-cap abort banner (SAFE-04)
expected: Construct a scenario where the agent loops past 5 steps (or manually reduce max_steps in settings); red error banner displays with exact D-22 copy; partial output expander shows last tool call if any.
result: [pending]

### 6. Starter gallery + pre-fill (ONBD-01)
expected: On empty Ask page, gallery shows 8 starter prompts in 4×2 grid; clicking fills the text area without auto-submitting; gallery hides once a question has been run.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
