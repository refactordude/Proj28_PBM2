<!-- GSD:project-start source:PROJECT.md -->
## Project

**PBM2**

PBM2 is an internal FastAPI + Bootstrap 5 + HTMX website where a team of non-SQL users (PMs, analysts) can browse and query a large, EAV-form MySQL parameter database (`ufs_data`) that stores UFS subsystem profiles of Android platforms. The app lets users slice, pivot, filter, visualize, and export this long-form data — and ask natural-language questions on top — without ever writing SQL or reasoning about the schema themselves.

**Core Value:** **Fast ad-hoc browsing of the parameter database.** Even if the NL layer fails, the UI must let a non-SQL user quickly find the platforms they care about, the parameters they care about, and see them in a wide-form grid they can read, compare, chart, and export. NL query rides on top of this and enhances it — it does not replace it.

### Constraints

- **Tech stack**: FastAPI + Bootstrap 5 + HTMX + Jinja2 + jinja2-fragments + SQLAlchemy (pymysql driver) + pandas + Pydantic v2 + python-dotenv — Why: v2.0 milestone shipped this stack 2026-04-29 (tag v2.0); v1.0 Streamlit shell sunset in quick task 260429-kn7.
- **Data**: Single-table EAV MySQL (`ufs_data`), read-only — Why: Real deployment; write path is owned by another system.
- **Scale**: ~100k+ rows across many platforms — Why: User flagged "too large"; a full dump must be pre-filtered before it hits the LLM, a chart, or an export.
- **Deployment**: Company intranet, shared team creds — Why: User selected this explicitly; no public-internet exposure is planned.
- **LLM choice**: OpenAI (cloud) + Ollama (local), user-switchable at runtime — Why: Lets users pick cloud for quality vs local for data-sensitivity situationally.
- **Result heterogeneity**: Type coercion is lazy and per-query, never global — Why: Same `Item` legitimately appears hex on one platform and decimal on another.
- **Security**: Readonly DB user is the primary SQL-injection backstop for the NL agent — Why: Even if the LLM generates harmful SQL, the DB can't execute writes.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
> **Stack as of v2.0 (2026-04-29):** FastAPI + Bootstrap 5 + HTMX + Jinja2 superseded Streamlit as the UI primitive. The table below is the original v1.0 research; entries marked Streamlit / streamlit-authenticator / nest-asyncio are no longer active dependencies. See `.planning/PROJECT.md` Constraints for the current stack.

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Web | FastAPI + Bootstrap 5.3 + HTMX 2.0 + Jinja2 + jinja2-fragments | v2.0 shell; Streamlit removed in 260429-kn7 |
| DB | SQLAlchemy 2.0 (sync) + pymysql | read-only, single table `ufs_data` |
| Data | pandas 3.x + openpyxl | pivot / coercion / export |
| NL agent | PydanticAI 1.x + openai SDK (dual `base_url`) | OpenAI Cloud + Ollama backends |
| Caching | cachetools TTLCache + threading.Lock | replaces Streamlit-era `st.cache_data` / `st.cache_resource` |

Full v1.0 research (Streamlit-era stack analysis): [`.planning/research/STACK.md`](.planning/research/STACK.md)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
