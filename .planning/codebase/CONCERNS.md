# Codebase Concerns — Cleanup Audit

**Analysis Date:** 2026-05-02
**Scan focus:** Streamlit-era dead code & v2.0 migration leftovers
**Scope:** Repo root, `app/`, `app_v2/`, `tests/`, `scripts/`, `config/`, `content/`, `.planning/`, `.streamlit/`, `__pycache__/`

> **TL;DR — the v1.0 Streamlit shell sunset (quick `260429-kn7`) was thorough at the
> Python source level: zero `import streamlit` / `streamlit_authenticator` / `nest_asyncio`
> remain in active code (only docstring/comment mentions). What it left behind is
> **(a)** a cluster of legacy NL-LLM adapters (`app/adapters/llm/{base,openai_adapter,ollama_adapter,registry}.py`)
> that are imported only by each other; **(b)** stale top-level scaffolding like
> `.streamlit/config.toml`, `__pycache__/streamlit_app.cpython-313.pyc`, `config/overview.example.yaml`;
> **(c)** a 200-line README.md still describing v1.0 + v2.0 as parallel "Phases 1–3 of 5".
> Quick Wins below have the highest confidence.

---

## Quick Wins (high-confidence safe-to-delete)

The following items have **no inbound imports**, **no test coverage**, and **no run-time consumer**. Cross-checked via `grep -rn` across `app/`, `app_v2/`, `tests/`, `scripts/`, and `config/`.

1. `__pycache__/streamlit_app.cpython-313.pyc` — bytecode for a `.py` file deleted in `260429-kn7`. Repo-root `__pycache__/` itself is gitignored but the pyc is still on disk locally. **Confidence: high.**
2. `.streamlit/config.toml` — Streamlit theme config (light/blue palette). Streamlit is gone. Whole `.streamlit/` directory can drop. **Confidence: high.**
3. `app/adapters/llm/base.py` — declares `LLMAdapter` ABC with `generate_sql` / `stream_text`. **Only consumers are siblings in the same package** (`openai_adapter.py`, `ollama_adapter.py`, `registry.py`). No v2 code touches them. **Confidence: high.**
4. `app/adapters/llm/openai_adapter.py` — legacy v1.0 `OpenAIAdapter`. Replaced by `app/adapters/llm/pydantic_model.py::build_pydantic_model` for the PydanticAI path. **Confidence: high.**
5. `app/adapters/llm/ollama_adapter.py` — legacy v1.0 `OllamaAdapter` (the only thing in the repo importing `requests`). Replaced by PydanticAI's `OllamaProvider`. **Confidence: high.**
6. `app/adapters/llm/registry.py` — legacy `build_adapter(LLMConfig)` factory. Only consumed by tests/imports of itself. The v2 entry point uses `app.adapters.db.registry.build_adapter` (DB only, not LLM). **Confidence: high.**
7. `requests>=2.32` line in `requirements.txt` — sole importer is `app/adapters/llm/ollama_adapter.py:11` (Quick Win #5). Once the adapter goes, drop the dep. **Confidence: high.**
8. `plotly>=5.22` line in `requirements.txt` — zero `import plotly` / `from plotly` in any `.py` file under `app/`, `app_v2/`, `tests/`, `scripts/`. Charts were a v1.0 Streamlit feature; v2.0 Browse is view-only by D-19..D-22. **Confidence: high.**
9. `altair>=5.3` line in `requirements.txt` — zero `import altair` / `from altair` anywhere. Carry-over from v1.0 STACK research. **Confidence: high.**
10. `bcrypt>=4.2` line in `requirements.txt` — zero `import bcrypt` / `from bcrypt`. It was a transitive dep of `streamlit-authenticator` per CLAUDE.md; that lib is already gone, the explicit pin can follow. **Confidence: high.**
11. `openpyxl>=3.1` line in `requirements.txt` — zero `import openpyxl` / `engine="openpyxl"`. Used only by v1.0 Excel export which retired with Streamlit per PROJECT.md "Out of Scope" entry. **Confidence: high.**
12. `config/overview.example.yaml` — Phase 5 curated-Platform watchlist scaffold. The whole feature (`overview_store.py`, `overview_filter.py`, `overview_grid_service.py`, `POST /overview/add`) was deleted per D-JV-06 / D-JV-07. The example template now has nothing to seed. **Confidence: high.**
13. README.md (root) — describes v2.0 as "Active — Phases 1–3 of 5", points users to `streamlit run app/main.py` (file does not exist), claims `app/` is "v1.0 Streamlit (shipped, frozen)" with Streamlit pages. Reality: v2.0 shipped 2026-04-29; `app/` is a shared library; further phases (Joint Validation, UI shell) shipped post-v2.0. **Confidence: high — needs rewrite, not deletion.**

---

## Dead Streamlit code

### Legacy LLM adapter cluster (closed unused subgraph)

**Files:**
- `app/adapters/llm/base.py` (36 lines) — `LLMAdapter` ABC with `generate_sql` + `stream_text` + `SQL_SYSTEM_PROMPT`
- `app/adapters/llm/openai_adapter.py` (78 lines) — `class OpenAIAdapter(LLMAdapter)`; uses `openai>=1.0` SDK + `httpx.Timeout`
- `app/adapters/llm/ollama_adapter.py` (79 lines) — `class OllamaAdapter(LLMAdapter)`; the **only** importer of `requests` in the repo (line 11)
- `app/adapters/llm/registry.py` (33 lines) — `_REGISTRY = {"openai": OpenAIAdapter, "ollama": OllamaAdapter}` and `build_adapter(LLMConfig)`

**Evidence (closed subgraph):**
```
$ grep -rn "from app.adapters.llm" app app_v2 tests | grep -v pydantic_model
app/adapters/llm/registry.py:9:  from app.adapters.llm.base import LLMAdapter
app/adapters/llm/registry.py:10: from app.adapters.llm.ollama_adapter import OllamaAdapter
app/adapters/llm/registry.py:11: from app.adapters.llm.openai_adapter import OpenAIAdapter
app/adapters/llm/openai_adapter.py:15: from app.adapters.llm.base import LLMAdapter, SQL_SYSTEM_PROMPT
app/adapters/llm/ollama_adapter.py:13: from app.adapters.llm.base import LLMAdapter, SQL_SYSTEM_PROMPT
```
No file outside this 4-file cluster imports any of them. `app_v2/main.py:30` imports `build_adapter` from `app.adapters.db.registry`, **not** `app.adapters.llm.registry`.

**Status:** v2.0 NL agent uses `app/adapters/llm/pydantic_model.py::build_pydantic_model` exclusively. The pydantic_model docstring even confirms it (line 3): *"This is a NEW parallel path — the legacy OpenAIAdapter / OllamaAdapter in this package remain for Phase 1 code (generate_sql / stream_text). The NL agent does NOT use them."* — but Phase 1 code (the v1.0 Streamlit Ask page) was deleted in 260429-kn7, so "Phase 1 code" no longer exists.

**Impact of removal:** ~226 lines deleted; `requests` dep can drop too. No test changes (the cluster is untested).

**Confidence:** HIGH.

---

### Stale Streamlit references in live code (cosmetic)

**`app_v2/services/starter_prompts.py:9`** — module docstring says:
> *"`app/pages/ask.py` calls `nest_asyncio.apply()` at module top (line 9) and imports `streamlit` — both incompatible with the FastAPI process"*

The referenced file `app/pages/ask.py` no longer exists (deleted by D-22 per PROJECT.md). Docstring is correct historically but actively misleads readers.

**`app_v2/routers/ask.py:54`** — comment in `_get_agent` says:
> *"Matches the v1.0 `get_nl_agent` `@st.cache_resource` pattern (RESEARCH.md Pattern 5)."*

Reference to `@st.cache_resource` is stale rationale; no Streamlit lives in this file.

**`app/services/sql_limiter.py:4`** — comment mentions "Pitfall 5".
**`app/core/agent/nl_service.py:27`** — docstring lists `streamlit` as an explicit non-dependency.

**Confidence:** HIGH — these are docstring/comment edits, not deletions. Low priority; safe to update during the broader sweep.

---

## Stale dependencies (`requirements.txt`)

Verified against `grep -rn 'import <pkg>\|from <pkg>'` across `app/`, `app_v2/`, `tests/`, `scripts/`:

| Line | Package | Importer found? | Disposition |
|------|---------|-----------------|-------------|
| `requests>=2.32` | `requests` | Only `app/adapters/llm/ollama_adapter.py:11` (legacy adapter, Quick Win #5) | **Drop after Quick Win #5.** |
| `plotly>=5.22` | `plotly` | None | **Drop.** v1.0 chart feature; v2.0 Browse is view-only. |
| `altair>=5.3` | `altair` | None | **Drop.** Never used; carry-over from v1.0 research. |
| `bcrypt>=4.2` | `bcrypt` | None | **Drop.** Was a transitive of `streamlit-authenticator`. |
| `openpyxl>=3.1` | `openpyxl` | None | **Drop.** v1.0 Excel export feature retired with Streamlit. |
| `sqlparse>=0.5` | `sqlparse` | Used by `app/services/sql_validator.py` (live) | **Keep.** |
| `httpx>=0.27` | `httpx` | Used by `app/adapters/llm/openai_adapter.py` (legacy, dies with cluster) AND transitively by `openai` SDK | Reassess after legacy LLM cluster goes — likely keep as transitive of `openai`/`pydantic-ai`. |

**Files:** `requirements.txt`
**Confidence:** HIGH for plotly/altair/bcrypt/openpyxl. HIGH for `requests` once Quick Win #5 lands. MEDIUM for `httpx` (depends on whether `openai` pins it transitively).

---

## Orphaned config files

### `.streamlit/config.toml`

**Path:** `.streamlit/config.toml` (whole directory orphan)
**Contents:** Streamlit theme (`primaryColor = "#1f77b4"`, etc.). Read by Streamlit at startup; nothing else parses TOML at this path.
**Evidence:** `grep -rn '\.streamlit\|streamlit/config'` in app code returns nothing.
**Confidence:** HIGH. Delete `.streamlit/` directory entirely.

### `config/overview.example.yaml`

**Path:** `config/overview.example.yaml` (committed; live `config/overview.yaml` is gitignored and per D-JV-07 is also retired)
**Contents:** `entities: []` template for the Phase 5 curated-Platform watchlist.
**Evidence:** `grep -rn 'config/overview'` returns four hits, **all in test files commenting on its deletion**:
```
tests/v2/test_phase03_invariants.py:23:  was deleted by Phase 1 Plan 06 alongside ``config/overview.yaml``.
tests/v2/test_phase03_invariants.py:209: cleanup) along with ``config/overview.yaml``.
tests/v2/test_summary_routes.py:92:    along with config/overview.yaml — the curated-Platform list is gone.
tests/v2/test_summary_integration.py:59: along with config/overview.yaml — the curated-Platform list is gone.
tests/v2/test_content_routes.py:56:    along with config/overview.yaml — the curated-Platform list is gone.
```
The committed `.example.yaml` template is the last user-facing surface of a feature that is gone.
**Confidence:** HIGH.

### `config/auth.yaml` references in docs (file itself does not exist)

**Path:** `config/` directory has **no** `auth.yaml` — already removed in 260429-kn7. But two doc files still reference it:
- `README.md:154` — *"`config/`: YAML configs — `settings.yaml`, `overview.yaml`, `starter_prompts.yaml`, `auth.yaml` (gitignored, examples committed)"*
- `CLAUDE.md:38` (in the v1.0 stack research table; the `> Stack as of v2.0` admonition above already disclaims it, but the table row is technically stale)

**Confidence:** MEDIUM — README needs editing in any case (see "Stale Documentation" below).

---

## Unused fixtures / test data

### `content/joint_validation/3193869100/ … 3193869175/` (16 stress-test fakes)

**Status:** **NOT dead.** Created in quick task `260502-jb2` to stress-test the JV grid pagination at `JV_PAGE_SIZE=15` (need ≥ 22 fixtures to see page 2). They are consumed at runtime by `app_v2/services/joint_validation_grid_service.py::build_joint_validation_grid_view_model(Path('content/joint_validation'), …)` at every `/overview` request.

**Note:** The whole `content/` tree is gitignored (`.gitignore:14-23`) so these fixtures don't bloat the repo, only local disk. **Do not delete.**

### `content/joint_validation/3193868109/ … 3193868600/` (6 baseline fixtures)

**Status:** Same as above — explicitly preserved per `260502-jb2-PLAN.md`: *"existing 6 ... untouched."* Consumed by tests via tmp_path mock copies and by the live `/overview` route. **Do not delete.**

### `tests/v2/fixtures/joint_validation_sample.html` + `joint_validation_fallback_sample.html`

Used by `tests/v2/test_joint_validation_parser.py` (selector parser + fallback path tests). **Active. Keep.**

### `data/demo_ufs.db`

Committed binary (24KB) referenced by `config/settings.yaml:4` (`database: data/demo_ufs.db`) and seeded by `scripts/seed_demo_db.py`. Used as the default SQLite backend for the FastAPI app at startup. **Active. Keep.**

---

## Archive candidates (do NOT delete — list only)

Per the user's request: list these for visibility; the `/gsd-cleanup` command handles them.

### Completed milestone archives

- `.planning/milestones/v1.0-phases/01-foundation-browsing/` (~796K with v2.0-phases) — 16 files; v1.0 is shipped and sunset.
- `.planning/milestones/v1.0-phases/02-nl-agent-layer/` — 14 files; same status.
- `.planning/milestones/v2.0-phases/01-pre-work-foundation/ … 06-ask-tab-port/` (~2.7M) — 6 phase directories; v2.0 shipped 2026-04-29.

### Old research files

- `.planning/research/v1.0/{ARCHITECTURE,FEATURES,PITFALLS,STACK,SUMMARY}.md` (164K) — pre-v1.0 stack research; superseded by `.planning/research/{STACK,ARCHITECTURE,...}.md` (which are the v2.0 rewrite research).

### Resolved debug entries

- `.planning/debug/resolved/260429-ask-tab-prompts-and-popover.md`
- `.planning/debug/resolved/260430-browse-pivot-empty-row-labels.md`

### Completed quick tasks (all 9 in `.planning/quick/`)

All are shipped per their SUMMARY.md files. Listed for completeness:
- `260427-uoh-add-sqlite-db-adapter-and-demo-data-seed`
- `260429-e76-fix-overview-filter-popover-clipping-ext`
- `260429-ek7-restyle-active-state-link-button-in-over`
- `260429-kc1-source-ufs-service-table-and-allowed-tab`
- `260429-kn7-remove-v1-0-streamlit-shell-app-v2-fasta`
- `260429-qyv-browse-parameters-filter-depends-on-sele`
- `260430-wzg-fix-joint-validation-filter-popover-clip`
- `260502-jb2-add-fake-joint-validation-fixture-folder`
- `260502-sqi-fix-jv-pagination-losing-sort-state-thre`

**Confidence:** HIGH that they are completed; **deletion policy is not for this scan to decide.**

---

## Misc cleanup candidates

### Stale `__pycache__/*.pyc` orphans (local-only; gitignored)

The repo-root `__pycache__/` is gitignored, but the directory itself exists locally and contains a smoking gun:

- `__pycache__/streamlit_app.cpython-313.pyc` — bytecode for `streamlit_app.py` (timestamp `Apr 24 01:00:24 2026`, 6320 source bytes). Source file does not exist. Last running artifact of the v1.0 Streamlit shell.

Also stale (orphan `.pyc` whose `.py` was deleted in 260429-kn7 / Phase 5 / D-JV-06):
- `app_v2/services/__pycache__/overview_store.cpython-313.pyc`
- `app_v2/services/__pycache__/overview_filter.cpython-313.pyc`
- `app_v2/services/__pycache__/overview_grid_service.cpython-313.pyc`

And `tests/v2/__pycache__/test_overview_{filter,store,grid_service,routes}.cpython-31{1,3}-pytest-*.pyc` — same story.

**Fix:** `find . -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +`. Local hygiene only — does not affect the repo.

**Confidence:** HIGH — these are pure cache; safe to wipe.

### Stale documentation: `README.md` (root)

**Path:** `/home/yh/Desktop/02_Projects/Proj28_PBM2/README.md`
**Status mismatches with PROJECT.md:**

| README claim | Reality (per `.planning/PROJECT.md`) |
|--------------|--------------------------------------|
| "v2.0 Bootstrap Shell — Active — Phases 1–3 of 5" (line 14) | v2.0 shipped 2026-04-29; 6 phases / 30 plans / 506 tests; tag `v2.0`. Two more milestones beyond v2.0 (JV auto-discovery, UI-shell rewrite + JV pagination) also shipped. |
| "413 passing tests" (line 14, 79) | Current: 442 passed / 5 skipped. |
| "Run v1.0 (Streamlit): `streamlit run app/main.py`" (lines 60-66) | `app/main.py` does not exist; Streamlit shell removed in `260429-kn7`. |
| "Browse and Ask still serve placeholder stubs until Phases 4–5 land" (line 74) | Browse (Phase 4) and Ask (Phase 6) ports both shipped. |
| "Phase 4 (Browse) and Phase 5 (Ask) port the v1.0 features under the new shell. Not yet started." (line 109) | Both shipped. |
| "v1.0 is preserved as-is in `app/` for rollback" (line 16) | `app/` is now a **shared library** (config + adapters + agent + services), not Streamlit. v1.0 Streamlit pages/components are gone. |
| `app/main.py / pages/ / components/` ASCII tree (lines 115-141) | None of those paths exist; current `app/` has only `core/`, `adapters/`, `services/`. |
| "`config/auth.yaml` (gitignored, examples committed)" (line 154) | `auth.yaml` removed; no `auth.example.yaml` ever existed. |
| "/gsd-autonomous --from 4    # Phases 4-5" (line 168) | Both phases shipped; this command is misleading. |

**Impact:** A user (or LLM) reading the README forms an entirely wrong mental model of the codebase. **High priority to rewrite.**
**Confidence:** HIGH.

### Stale documentation: `CLAUDE.md`

**Path:** `/home/yh/Desktop/02_Projects/Proj28_PBM2/CLAUDE.md`
**Status:** The `> Stack as of v2.0` admonition (line 22) correctly disclaims the table that follows — *"entries marked Streamlit / streamlit-authenticator / nest-asyncio are no longer active dependencies."* — but the table itself remains and includes 12+ rows of v1.0 research output (Streamlit 1.56, streamlit-authenticator 0.4.2, st.dataframe, st.cache_data, AppTest, Streamlit AppTest testing strategy, etc.). The `## Constraints` section at the top is correctly the v2.0 stack.

**Impact:** Wall of stale text in the per-project Claude memory. Tokens that the LLM has to read on every conversation.
**Confidence:** HIGH that the table contents are stale; LOW on whether to delete vs trim — the admonition argues for keeping (historical record). **Recommend trim to a 5-line "v2.0 stack at a glance" box** and link to `.planning/research/STACK.md` for the full v2 research.

### `.env.example`

**Path:** `/home/yh/Desktop/02_Projects/Proj28_PBM2/.env.example`
**Issue:** No mention of the v2 stack (still references `SETTINGS_PATH`, `AUTH_PATH`, `LOG_DIR`). `AUTH_PATH` was for `streamlit-authenticator`. The PROJECT.md says auth is deferred; `AUTH_PATH` is currently unused.
**Confidence:** MEDIUM — drop `AUTH_PATH` line; keep file otherwise.

---

## Needs Investigation (deletion safety unclear)

### `app/adapters/db/sqlite.py` and SQLite path in `app/adapters/db/registry.py`

**Files:** `app/adapters/db/sqlite.py` (`class SQLiteAdapter(DBAdapter)`)
**Evidence:** The current `config/settings.yaml:1-5` selects `"Demo SQLite"` (`type: sqlite`, `database: data/demo_ufs.db`) as the default DB, and `scripts/seed_demo_db.py` exists to populate it. So this is **not** dead — but it's worth confirming: is the SQLite adapter only for local-dev demo, or does any deployed setup rely on it?

Per `.planning/quick/260427-uoh-add-sqlite-db-adapter-and-demo-data-seed/`, this was added explicitly for v2.0 UAT. Likely **keep** but document the demo-only intent in a docstring.

**Confidence:** MEDIUM — leave alone unless the user wants to enforce "MySQL only".

### Python version drift in `__pycache__`

`*.cpython-311-*.pyc` and `*.cpython-313-*.pyc` co-exist throughout. `pyproject` is not present; CLAUDE.md / README.md mention Python 3.13. If the team has standardized on 3.13 the 311-pyc files are stale builds from a previous interpreter. Cosmetic only (gitignored).

**Confidence:** LOW (no harm).

### `httpx>=0.27` in `requirements.txt`

Direct importer is `app/adapters/llm/openai_adapter.py:12` (legacy cluster). After Quick Win #5 lands, no `import httpx` will remain in `app/`. But `openai` SDK and `pydantic-ai` both pin `httpx` transitively, so removing the explicit pin would let those float. Either:
- (a) drop the direct pin and let transitive resolution handle it, or
- (b) keep the direct pin for reproducibility.

Either is defensible. **Confidence:** LOW.

### `data/demo_ufs.db` (committed 24KB binary)

Used by `config/settings.yaml`'s default DB. Useful for v2 UAT and pytest smoke. Keep — but confirm whether team wants to commit a binary (it could be regenerated by `scripts/seed_demo_db.py`).

**Confidence:** LOW — committed-binary tradeoff is a team policy call, not a dead-code call.

### `config/settings.yaml` (gitignored, working tree only) — security note

**Path:** `config/settings.yaml`
**Issue:** Contains a real-looking OpenAI API key on line 11 (`sk-proj-jJMX...HzwA`, ~163 chars). File **is** gitignored (`.gitignore:2`) and **was never committed** (`git log --all --full-history -- config/settings.yaml` returns empty). So the key has not leaked to the repo's history.

**Action:** Not a cleanup task; flag to the user — if that key is real, rotate it (it's now sitting in plaintext in the working tree at all times) and consider moving the value to `.env` + `OPENAI_API_KEY` so it is never on-disk in a YAML.

**Confidence:** HIGH that this is gitignored and never committed; HIGH that it is best practice to move it to `.env`.

---

## Summary table

| Finding | Path | Action | Confidence |
|---------|------|--------|------------|
| Legacy LLM adapter cluster | `app/adapters/llm/{base,openai_adapter,ollama_adapter,registry}.py` | Delete (~226 lines) | HIGH |
| Stale Streamlit dir | `.streamlit/config.toml` (and parent dir) | Delete | HIGH |
| Stale bytecode | `__pycache__/streamlit_app.cpython-313.pyc` | Delete (and parent `__pycache__/`) | HIGH |
| Orphan example | `config/overview.example.yaml` | Delete | HIGH |
| Stale dep | `requirements.txt: requests` | Drop after legacy LLM cluster removed | HIGH |
| Stale dep | `requirements.txt: plotly` | Drop | HIGH |
| Stale dep | `requirements.txt: altair` | Drop | HIGH |
| Stale dep | `requirements.txt: bcrypt` | Drop | HIGH |
| Stale dep | `requirements.txt: openpyxl` | Drop | HIGH |
| Stale README | `README.md` | Rewrite (status table, structure tree, run commands) | HIGH |
| Stale CLAUDE table | `CLAUDE.md` (the v1.0 STACK table) | Trim to a v2.0 summary | HIGH (content) / MED (policy) |
| Stale `.env.example` line | `.env.example: AUTH_PATH` | Remove | MEDIUM |
| Stale comments/docstrings | `app_v2/routers/ask.py:54`, `app_v2/services/starter_prompts.py:9-13`, `app/core/agent/nl_service.py:27` | Edit | LOW (cosmetic) |
| Archive candidates | `.planning/milestones/v1.0-phases/`, `.planning/milestones/v2.0-phases/`, `.planning/research/v1.0/` | List only — `/gsd-cleanup` handles | n/a |
| API key in working tree | `config/settings.yaml` (gitignored) | Rotate + move to `.env` | HIGH (security advice) |

**Estimated impact of executing all HIGH-confidence Quick Wins:**
- **5 deps** removed from `requirements.txt`
- **6 source files** deleted (legacy LLM cluster + 1 example yaml)
- **~226 LOC** Python deleted
- **2 directories** removed (`.streamlit/`, repo-root `__pycache__/`)
- **README.md + CLAUDE.md** rewrites (largest reader-time impact)
- Zero test changes required (the legacy LLM cluster has no tests)

---

*Concerns audit: 2026-05-02*
