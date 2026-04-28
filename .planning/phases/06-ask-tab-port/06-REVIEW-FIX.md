---
phase: 06-ask-tab-port
fixed_at: 2026-04-29T00:00:00Z
review_path: .planning/phases/06-ask-tab-port/06-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-04-29
**Source review:** `.planning/phases/06-ask-tab-port/06-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (Critical: 0, Warning: 2; Info: 5 deferred per `fix_scope=critical_warning`)
- Fixed: 2
- Skipped: 0
- Regression bar: 339 passed / 2 skipped (`pytest tests/v2/ -q`) — unchanged from pre-fix baseline.

## Fixed Issues

### WR-01: Unconfigured-LLM error message is awkwardly wrapped by the generic abort-banner template

**Files modified:** `app_v2/routers/ask.py`, `app_v2/templates/ask/_abort_banner.html`
**Commit:** `1995e89`
**Applied fix:**
- Added a fourth `{% elif reason == "unconfigured" %}` branch in `_abort_banner.html` rendering a single actionable line: *"No LLM backend configured. Open Settings and select a backend, then try again."*
- Updated the docstring `Context shape provided by routes` enum to include `"unconfigured"`.
- Changed `_render_unconfigured` in `ask.py` to set `reason="unconfigured"` (was `"llm-error"`) and pass empty `detail=""` (the message now lives in the template, not a parenthesised injection). Added a docstring noting the WR-01 rationale.
- Existing test `test_post_ask_query_no_llm_configured_returns_abort_banner` still asserts on the exact substring `"No LLM backend configured"`, so the contract is preserved.

### WR-02: Second-turn ClarificationNeeded suppression yields generic "Something went wrong" copy with no recovery hint

**Files modified:** `app_v2/routers/ask.py`, `app_v2/templates/ask/_abort_banner.html`
**Commit:** `f06fb88`
**Applied fix:**
- Added a fifth `{% elif reason == "loop-aborted" %}` branch in `_abort_banner.html` with copy that explicitly tells the user the model could not narrow their question even with explicit parameters and instructs them to edit the question (mentioning platform IDs, parameter names, or a value range).
- Updated the docstring `Context shape provided by routes` enum to include `"loop-aborted"`.
- Replaced the synthesized `AgentRunFailure(reason="llm-error", ...)` + `_render_failure_kind` path in `_run_second_turn` with a direct `templates.TemplateResponse(...)` call carrying `reason="loop-aborted"`. The local `from app.core.agent.nl_agent import AgentRunFailure` import is removed as a side effect (a passing improvement on IN-01 for this code path; the top-level coupling already exists via `AgentDeps`/`build_agent`).
- Domain model `AgentRunFailure.reason` (a `Literal["step-cap", "timeout", "llm-error"]`) is intentionally NOT widened — the reason value is a v2 presentation concern, not an agent-output concern, so it lives at the route layer.
- Existing regression test `test_post_ask_confirm_second_turn_clarification_is_suppressed` still passes because it accepts either `"Something went wrong"` OR `"clarification a second time"` in the body, and the new copy contains the latter substring (`"clarification a second time was suppressed"`).
- Note: this is a copy/UX fix verified by Tier 2 syntax checks plus the full v2 regression suite — no logic-bug verification flag needed.

## Skipped Issues

None — both Warning findings were applied cleanly. The five Info findings (IN-01..IN-05) are out of scope per `fix_scope=critical_warning` and remain documented in `06-REVIEW.md` for follow-up consideration.

---

_Fixed: 2026-04-29_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
