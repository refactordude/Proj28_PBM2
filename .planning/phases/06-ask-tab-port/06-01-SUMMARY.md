---
phase: 06-ask-tab-port
plan: "01"
subsystem: planning-docs
tags: [spec-deviation, requirements, roadmap, docs-only]
dependency_graph:
  requires: []
  provides: [post-deviation-spec]
  affects: [.planning/REQUIREMENTS.md, .planning/ROADMAP.md]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
decisions:
  - "ASK-V2-04 removed from active Phase 6 list; folded into ASK-V2-F01 (D-05)"
  - "ASK-V2-03 Regenerate clause dropped; D-11 parenthetical added"
  - "ASK-V2-05 rewritten: Ask-page-only selector + no OpenAI banner (D-12, D-18)"
  - "ROADMAP Phase 6 SC#3 rewritten to drop banner sub-claims (D-12 + D-18)"
metrics:
  duration: "~3 minutes"
  completed: "2026-04-29"
  tasks_completed: 2
  files_modified: 2
---

# Phase 6 Plan 01: Spec Deviations Summary

**One-liner:** Applied 3 Phase 6 spec deviations (no Regenerate, no history panel, Ask-page-only LLM selector with no OpenAI banner) to REQUIREMENTS.md and ROADMAP.md so Plans 06-02..06-06 build against the corrected spec.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Apply ASK-V2-03/04/05 deviations to REQUIREMENTS.md | 4cd3dc1 | .planning/REQUIREMENTS.md |
| 2 | Reconcile ROADMAP Phase 6 Success Criterion #3 | 160e28f | .planning/ROADMAP.md |

## Sub-edits Applied

### REQUIREMENTS.md — 4 sub-edits

**(1) ASK-V2-03 — Drop Regenerate clause (D-11)**

Removed the trailing sentence "Regenerate button above the summary re-invokes the agent with the same question + confirmed params via HTMX." Replaced with a D-11 parenthetical: "no Regenerate button — editing the textarea and clicking Run is the regeneration mechanism." The table/summary/SQL expander content stays intact.

**(2) ASK-V2-04 — Remove from active list; subsume into ASK-V2-F01 (D-05)**

The entire ASK-V2-04 bullet ("Session history panel, max 50 entries LRU, signed cookie or app.state") was deleted from the active "Ask Tab (Port)" section. The existing `ASK-V2-F01` bullet was expanded to explicitly subsume ASK-V2-04's scope, noting Phase 6 ships zero history surface area (single-shot Q→A only).

**(3) ASK-V2-05 — Rewrite to Ask-page-only selector + no OpenAI banner (D-12, D-18)**

Dropped both the "global sidebar (top-right of the Bootstrap nav, a `<select>`...)" placement clause and the entire dismissible OpenAI alert banner clause. Replaced with the post-deviation text specifying: Bootstrap dropdown in a page-header strip at `/ask` ONLY, `pbm2_llm` plain unsigned cookie, validation against `settings.llms[].name`, global cookie effect via `llm_resolver`, and explicit statement of NO sensitivity-warning banner.

**(4a) Traceability table — ASK-V2-04 row updated**

Changed `| ASK-V2-04 | Phase 6 | Pending |` to `| ASK-V2-04 | (deferred — see ASK-V2-F01) | Out of Scope |`.

**(4b) Totals reconciled**

| Field | Before | After |
|-------|--------|-------|
| v2.0 Requirements | 51 | 50 |
| ASK-V2 count | 8 | 7 |
| Mapped reqs | 45 / 45 | 44 / 44 |
| Phase 5 count | 8 (was overcounted) | 6 |
| Phase 6 count | (absent) | 7 |

### ROADMAP.md — 1 edit

**Phase 6 Success Criterion #3 rewrite (D-12 + D-18)**

Replaced the obsolete SC#3 ("Switching the backend selector to OpenAI shows the data-sensitivity alert banner; the selected backend persists across page refreshes (cookie); switching back to Ollama clears the banner") with the post-deviation criterion referencing the `"LLM: Ollama ▾"` / `"LLM: OpenAI ▾"` dropdown, `pbm2_llm` cookie persistence, and the explicit note that there is no OpenAI sensitivity-warning banner anywhere (D-12 + D-18).

## Downstream Plans Unblocked

Plans 06-02..06-06 can now reference the post-deviation requirement IDs without spec mismatch:

- **06-02** (llm_resolver extension) — can reference D-15/D-17 and ASK-V2-05 without the global-navbar placement or banner wiring
- **06-03** (ask + settings routers) — can implement `POST /settings/llm` + 204 + HX-Refresh without any banner fragment
- **06-04** (ask templates) — can build the page-header LLM dropdown without `_openai_banner.html` partial
- **06-05** (tests) — test assertions for ASK-V2-05 match the cookie-only selector behavior, not the banner flow
- **06-06** (v1.0 Ask deletion) — ASK-V2-04 absence from active list means test-count delta calculation excludes history-panel tests

## Locked Decisions Backing Each Deviation

| Deviation | Decision ID | Text in CONTEXT.md |
|-----------|-------------|-------------------|
| No Regenerate button | D-11 | "No Regenerate button. The user explicitly chose 'edit textarea + Ask again' as the regeneration mechanism" |
| No history panel (ASK-V2-04 out) | D-05 | "No history panel. ASK-V2-04 is moved to Out of Scope. Phase 6 ships zero history surface area: no widget, no cookie, no app.state list, no LRU." |
| Ask-page-only selector (ASK-V2-05 placement) | D-12 | "Selector placement: a small page-header strip at the top of /ask only (NOT the global base.html navbar)" |
| No OpenAI banner (ASK-V2-05 banner) | D-18 | "No OpenAI sensitivity-warning banner. Phase 6 ships no .alert.alert-warning for OpenAI usage anywhere." |

## Deviations from Plan

None — plan executed exactly as written. All 4 REQUIREMENTS.md sub-edits and the single ROADMAP.md edit applied verbatim per plan instructions.

## Self-Check: PASSED

- `.planning/REQUIREMENTS.md` — modified, exists: FOUND
- `.planning/ROADMAP.md` — modified, exists: FOUND
- Commit 4cd3dc1 (Task 1): FOUND
- Commit 160e28f (Task 2): FOUND
- Zero production code changes: VERIFIED (`git diff HEAD~2 -- app/ app_v2/ tests/ streamlit_app.py | wc -l` = 0)
- All 9 REQUIREMENTS.md grep assertions: PASSED
- All 5 ROADMAP.md grep assertions: PASSED
