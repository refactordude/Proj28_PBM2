"""Phase 04 — Browse routes integration tests.

Exercises GET /browse + POST /browse/grid through the FastAPI TestClient
with stubbed cache layer (no real MySQL). Verifies:
  - URL round-trip (BROWSE-V2-05) — query params survive a GET → render → form-submit cycle
  - Empty state copy (D-25) — verbatim 'Select platforms and parameters above…'
  - Cap warnings (D-24) — verbatim row-cap + col-cap copy
  - HX-Push-Url response header (D-32, Pitfall 2) — points at /browse, not /browse/grid
  - OOB count caption swap (D-06, Pattern 6)
  - XSS defense (autoescape + | e on every dynamic output)
  - SQL injection defense via parameterized binds (T-04-02-01)
  - Swap axes (D-16) — view transform changes index_col_name
  - Garbage param labels are dropped BEFORE SQL bind (T-04-02-02)

Cache layer is patched at the BROWSE_SERVICE call-site, not at cache module,
because browse_service does `from app_v2.services.cache import ...` which
binds the names into browse_service's namespace.

Note on form encoding: httpx 0.28 dropped support for the list-of-tuples
shape on the `data=` kwarg (raises TypeError). To send repeated form keys
(e.g. multiple `platforms` selections — the standard HTML form pattern), we
manually url-encode the body and pass it via `content=` with an explicit
`Content-Type: application/x-www-form-urlencoded` header. The helper
`_post_form_pairs(client, url, pairs)` wraps this idiom.
"""
from __future__ import annotations

from unittest.mock import MagicMock
from urllib.parse import urlencode

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app_v2.main import app


_FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}


def _post_form_pairs(client: TestClient, url: str, pairs):
    """POST with a manually-encoded form body to support repeated keys.

    httpx 0.28's `data=` no longer accepts list-of-tuples (raises TypeError);
    `content=` + explicit Content-Type is the supported escape hatch.
    """
    body = urlencode(list(pairs))
    return client.post(url, content=body, headers=_FORM_HEADERS)


class MockConfig:
    name = "test_db"


class MockDB:
    config = MockConfig()
    # No real engine; all ufs_service calls are patched out at the cache layer.


def _patch_cache(monkeypatch, *, platforms=None, params=None, fetch=None):
    """Patch cache layer at browse_service call-site (the import binding).

    platforms: list[str] — return value of list_platforms
    params: list[dict]   — return value of list_parameters; each dict has
                           'InfoCategory' and 'Item' keys
    fetch: callable      — replaces fetch_cells; signature
                           (db, platforms_tuple, infocategories_tuple, items_tuple, row_cap=200, db_name="")
                           returns (DataFrame, bool)
    """
    if platforms is not None:
        monkeypatch.setattr(
            "app_v2.services.browse_service.list_platforms",
            lambda db, db_name="": list(platforms),
        )
    if params is not None:
        monkeypatch.setattr(
            "app_v2.services.browse_service.list_parameters",
            lambda db, db_name="": list(params),
        )
    if fetch is not None:
        monkeypatch.setattr(
            "app_v2.services.browse_service.fetch_cells", fetch,
        )


@pytest.fixture
def client(monkeypatch):
    """TestClient with MockDB on app.state.db AFTER lifespan ran.

    Mirrors the Phase 03 isolated_summary fixture pattern — replacing
    app.state.db AFTER the context manager enters.
    """
    with TestClient(app) as c:
        app.state.db = MockDB()
        yield c
        app.state.db = None


# -----------------------------------------------------------------------
# GET /browse — empty + URL-pre-checked + grid pre-rendered
# -----------------------------------------------------------------------

def test_get_browse_empty_state(client, monkeypatch):
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ])
    r = client.get("/browse")
    assert r.status_code == 200
    # D-25 verbatim empty-state copy
    assert "Select platforms and parameters above to build the pivot grid." in r.text
    # MUST NOT contain v1.0 wording
    assert "in the sidebar" not in r.text
    # Pickers render but no platform checkbox is checked.
    # Find the input element referencing P1 and ensure no `checked` shows up
    # within that input's tag boundaries.
    assert 'value="P1"' in r.text
    i = r.text.index('value="P1"')
    seg_start = r.text.rfind("<input", 0, i)
    seg_end = r.text.find(">", i)
    assert seg_start != -1 and seg_end != -1
    seg = r.text[seg_start:seg_end]
    assert "checked" not in seg, f"Empty-state should not pre-check any platform checkbox: {seg}"


def test_get_browse_pre_checks_pickers_from_url(client, monkeypatch):
    _patch_cache(monkeypatch, platforms=["P1", "P2"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ], fetch=lambda db, p, ic, i, row_cap=200, db_name="": (
        pd.DataFrame({
            "PLATFORM_ID": ["P1"], "InfoCategory": ["attribute"],
            "Item": ["vendor_id"], "Result": ["0xA1"],
        }), False,
    ))
    r = client.get("/browse?platforms=P1&params=attribute%20%C2%B7%20vendor_id&swap=1")
    assert r.status_code == 200
    # Platform P1 checkbox is pre-checked
    assert 'value="P1"' in r.text
    # The pre-checked checkbox carries the `checked` attribute on the input
    # element itself.
    i = r.text.index('value="P1"')
    seg_start = r.text.rfind("<input", 0, i)
    seg_end = r.text.find(">", i)
    seg = r.text[seg_start:seg_end]
    assert "checked" in seg, f"P1 checkbox should be pre-checked; got input: {seg}"
    # Swap toggle is checked
    assert 'id="browse-swap-axes"' in r.text
    j = r.text.index('id="browse-swap-axes"')
    swap_seg_end = r.text.find(">", j)
    swap_seg = r.text[j:swap_seg_end]
    assert "checked" in swap_seg, f"Swap-axes input should be checked: {swap_seg}"


def test_get_browse_renders_grid_when_url_has_full_state(client, monkeypatch):
    _patch_cache(monkeypatch, platforms=["P1", "P2"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ], fetch=lambda db, p, ic, i, row_cap=200, db_name="": (
        pd.DataFrame({
            "PLATFORM_ID": ["P1", "P2"], "InfoCategory": ["attribute"] * 2,
            "Item": ["vendor_id"] * 2, "Result": ["0xA1", "0xA2"],
        }), False,
    ))
    r = client.get("/browse?platforms=P1&platforms=P2&params=attribute%20%C2%B7%20vendor_id")
    assert r.status_code == 200
    assert 'class="table table-striped table-hover table-sm pivot-table"' in r.text
    # Both result values present (Jinja-escaped but recognizable)
    assert "0xA1" in r.text
    assert "0xA2" in r.text


# -----------------------------------------------------------------------
# POST /browse/grid — fragment, HX-Push-Url, caps, OOB, empty
# -----------------------------------------------------------------------

def test_post_browse_grid_returns_fragment_not_full_page(client, monkeypatch):
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ], fetch=lambda db, p, ic, i, row_cap=200, db_name="": (
        pd.DataFrame({
            "PLATFORM_ID": ["P1"], "InfoCategory": ["attribute"],
            "Item": ["vendor_id"], "Result": ["0xA1"],
        }), False,
    ))
    r = _post_form_pairs(client, "/browse/grid", [
        ("platforms", "P1"),
        ("params", "attribute · vendor_id"),
    ])
    assert r.status_code == 200
    # Fragment — no full-page chrome
    assert "<html" not in r.text.lower()
    assert 'class="navbar' not in r.text
    # Has the table
    assert "pivot-table" in r.text
    # OOB span emitted with hx-swap-oob
    assert 'hx-swap-oob="true"' in r.text
    assert 'id="grid-count"' in r.text


def test_post_browse_grid_sets_hx_push_url_header(client, monkeypatch):
    _patch_cache(monkeypatch, platforms=["A", "B"], params=[
        {"InfoCategory": "cat", "Item": "item"},
    ], fetch=lambda db, p, ic, i, row_cap=200, db_name="": (
        pd.DataFrame({
            "PLATFORM_ID": ["A"], "InfoCategory": ["cat"],
            "Item": ["item"], "Result": ["v"],
        }), False,
    ))
    r = _post_form_pairs(client, "/browse/grid", [
        ("platforms", "A"), ("platforms", "B"),
        ("params", "cat · item"),
        ("swap", "1"),
    ])
    assert r.status_code == 200
    assert "HX-Push-Url" in r.headers
    push = r.headers["HX-Push-Url"]
    # URL-style %20 spaces and %C2%B7 middle-dot
    assert push == "/browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1", push
    # NOT /browse/grid (Pitfall 2 defended)
    assert "/browse/grid" not in push


def test_post_browse_grid_empty_form_returns_empty_state(client, monkeypatch):
    def _no_call(*args, **kwargs):
        raise AssertionError("fetch_cells must NOT be called when selection is empty")
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ], fetch=_no_call)
    r = _post_form_pairs(client, "/browse/grid", [])
    assert r.status_code == 200
    assert "Select platforms and parameters above to build the pivot grid." in r.text
    # Empty-state HX-Push-Url is plain /browse (no query string)
    assert r.headers.get("HX-Push-Url") == "/browse"


def test_post_browse_grid_row_cap_warning(client, monkeypatch):
    # 1 row of data with row_capped=True — the BOOLEAN drives the warning
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ], fetch=lambda db, p, ic, i, row_cap=200, db_name="": (
        pd.DataFrame({
            "PLATFORM_ID": ["P1"], "InfoCategory": ["attribute"],
            "Item": ["vendor_id"], "Result": ["0xA1"],
        }), True,  # row_capped
    ))
    r = _post_form_pairs(client, "/browse/grid", [
        ("platforms", "P1"),
        ("params", "attribute · vendor_id"),
    ])
    assert r.status_code == 200
    # D-24 verbatim row-cap copy
    assert "Result capped at 200 rows. Narrow your platform or parameter selection to see all data." in r.text


def test_post_browse_grid_col_cap_warning(client, monkeypatch):
    # 35 selected param labels with cat="attribute" and items "i00".."i34".
    # Stubbed fetch_cells returns a long DataFrame containing all 35 items
    # for one platform; pivot_to_wide (real, not mocked) caps at 30.
    labels = [f"attribute · i{n:02d}" for n in range(35)]
    long_df = pd.DataFrame({
        "PLATFORM_ID": ["P1"] * 35,
        "InfoCategory": ["attribute"] * 35,
        "Item": [f"i{n:02d}" for n in range(35)],
        "Result": [f"v{n}" for n in range(35)],
    })
    _patch_cache(
        monkeypatch,
        platforms=["P1"],
        params=[{"InfoCategory": "attribute", "Item": f"i{n:02d}"} for n in range(35)],
        fetch=lambda db, p, ic, i, row_cap=200, db_name="": (long_df, False),
    )
    form = [("platforms", "P1")] + [("params", lbl) for lbl in labels]
    r = _post_form_pairs(client, "/browse/grid", form)
    assert r.status_code == 200
    # D-24 verbatim col-cap copy with N=35
    assert "Showing first 30 of 35 parameters. Narrow your selection to see all." in r.text


# -----------------------------------------------------------------------
# XSS / SQLi defenses (T-04-03-02, T-04-02-01)
# -----------------------------------------------------------------------

def test_post_browse_grid_xss_escape_in_param_label(client, monkeypatch):
    # Hostile InfoCategory + Item — should be escaped in checkbox value attr,
    # in <span>, in data-label, in title.
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "<script>", "Item": "alert(1)</script>"},
    ])
    r = client.get("/browse")
    assert r.status_code == 200
    # The literal payload MUST NOT appear unescaped
    assert "<script>alert(1)</script>" not in r.text, "XSS via parameter label leaked into HTML"
    # The escaped form MUST appear (autoescape + | e). Jinja2 default uses &lt; &gt;.
    assert "&lt;script&gt;" in r.text or "&lt;script&gt" in r.text


def test_post_browse_grid_sql_injection_attempt_returns_safe(client, monkeypatch):
    # Two-part assertion:
    #   1) POST /browse/grid: the injection string flows to fetch_cells as a
    #      literal tuple element (no SQL interpolation possible — fetch_cells_core
    #      uses sa.bindparam(..., expanding=True) upstream).
    #   2) GET /browse with the same value: the string is HTML-escaped wherever
    #      echoed in the rendered popover checkbox values (XSS defense).
    captured: dict = {}

    def _capture(db, p, ic, i, row_cap=200, db_name=""):
        captured["platforms"] = p
        captured["infocategories"] = ic
        captured["items"] = i
        return (pd.DataFrame(columns=["PLATFORM_ID", "InfoCategory", "Item", "Result"]), False)

    injection = "' OR 1=1 --"
    # Make the catalog include the injection string so the GET render echoes it
    # in the platforms picker (where the XSS defense matters).
    _patch_cache(monkeypatch, platforms=["P1", injection], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ], fetch=_capture)

    # 1) POST → fetch_cells receives the injection string as a literal tuple
    #    element. NEVER interpolated into SQL.
    r_post = _post_form_pairs(client, "/browse/grid", [
        ("platforms", injection),
        ("params", "attribute · vendor_id"),
    ])
    assert r_post.status_code == 200
    assert captured["platforms"] == (injection,)
    # No literal <script> ever smuggled into the grid fragment response
    assert "<script" not in r_post.text

    # 2) GET /browse renders the platforms picker which echoes every catalog
    #    value into a checkbox `value="..."` — the injection string MUST be
    #    HTML-escaped there. Jinja2 default autoescape uses &#39; for the
    #    apostrophe (alternative forms accepted defensively).
    r_get = client.get(f"/browse?platforms={urlencode([('x', injection)])[2:]}")
    assert r_get.status_code == 200
    assert (
        "&#39; OR 1=1 --" in r_get.text
        or "&#x27; OR 1=1 --" in r_get.text
        or "&apos; OR 1=1 --" in r_get.text
    ), "Injection string should be HTML-escaped where echoed"
    # And no literal <script> even on the full page render
    assert "<script>" not in r_get.text or r_get.text.count("<script>") == 0


# -----------------------------------------------------------------------
# Swap axes (D-16, BROWSE-V2-01)
# -----------------------------------------------------------------------

def test_post_browse_grid_swap_axes_changes_index_col(client, monkeypatch):
    df_long = pd.DataFrame({
        "PLATFORM_ID": ["P1"], "InfoCategory": ["attribute"],
        "Item": ["vendor_id"], "Result": ["0xA1"],
    })
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ], fetch=lambda db, p, ic, i, row_cap=200, db_name="": (df_long, False))

    # Default (no swap): index is PLATFORM_ID
    r1 = _post_form_pairs(client, "/browse/grid", [
        ("platforms", "P1"), ("params", "attribute · vendor_id"),
    ])
    assert r1.status_code == 200
    # First <th> in thead contains the index col name
    assert "PLATFORM_ID" in r1.text

    # With swap=1: index becomes Item — appears as a <th> entry in thead.
    r2 = _post_form_pairs(client, "/browse/grid", [
        ("platforms", "P1"), ("params", "attribute · vendor_id"), ("swap", "1"),
    ])
    assert r2.status_code == 200
    # Index col name is now "Item"
    assert ">Item<" in r2.text or '"Item"' in r2.text


# -----------------------------------------------------------------------
# Garbage URL params do not blow up (T-04-02-02 mitigation — REAL assertion)
# -----------------------------------------------------------------------

def test_get_browse_with_garbage_params_returns_empty_grid(client, monkeypatch):
    """T-04-02-02: garbage param values must produce empty SQL filters, not crash or echo unsanitized.

    The previous version of this test had a tautological final assertion
    that compared a constant escaped string to a constant raw string —
    always True regardless of route behavior. This version captures
    fetch_cells's args and asserts the malformed label was DROPPED BEFORE
    the SQL layer — proving _parse_param_label returns None for labels
    without ' · ' and the comprehension filters them out.
    """
    # Use a recording mock so we can introspect the items/infocategories tuples.
    mock_fetch_cells = MagicMock(
        return_value=(pd.DataFrame(columns=["PLATFORM_ID", "InfoCategory", "Item", "Result"]), False)
    )
    _patch_cache(
        monkeypatch,
        platforms=["P1"],
        params=[{"InfoCategory": "attribute", "Item": "vendor_id"}],
        fetch=mock_fetch_cells,
    )
    r = client.get("/browse?params=garbage_no_separator&platforms=NONEXISTENT")
    assert r.status_code == 200
    # Empty-state OR a 0-row table — both are acceptable end-user surfaces.
    # Note: with platforms=NONEXISTENT and params=garbage, selected_platforms is
    # non-empty but selected_param_labels round-trips to an empty parsed list AT
    # THE SQL LAYER. The empty-selection short-circuit checks the RAW labels list
    # (which has one entry), so we land in the SQL branch with an empty items
    # tuple and 0-row DataFrame — _grid.html renders an empty table.
    assert (
        "Select platforms and parameters above" in r.text
        or "<tbody></tbody>" in r.text
        or "<tbody>\n            </tbody>" in r.text
        or "<tbody>" in r.text  # whitespace-only tbody from Jinja whitespace control
    )
    # Critical: verify garbage label did NOT reach the DB as a filter literal.
    # browse_service drops labels that don't contain the ' · ' separator BEFORE
    # constructing the items tuple. Per Plan 04-02 line 297-304, fetch_cells is
    # called as: fetch_cells(db, platforms_tuple, infocategories_tuple, items_tuple, row_cap=, db_name=)
    # Items is the 4th positional arg (index 3).
    assert mock_fetch_cells.called, "fetch_cells should be called once selection has both platforms and params (even garbage)"
    call_args = mock_fetch_cells.call_args.args or ()
    call_kwargs = mock_fetch_cells.call_args.kwargs or {}
    # items is positional arg index 3 (db, platforms, infocategories, items, ...)
    if "items" in call_kwargs:
        items_passed = call_kwargs["items"]
    elif len(call_args) > 3:
        items_passed = call_args[3]
    else:
        items_passed = None
    assert items_passed in (None, (), [], frozenset()), (
        f"garbage label leaked into items: {items_passed!r}"
    )
    # Also verify infocategories (positional arg 2) is empty for the same reason
    if "infocategories" in call_kwargs:
        ic_passed = call_kwargs["infocategories"]
    elif len(call_args) > 2:
        ic_passed = call_args[2]
    else:
        ic_passed = None
    assert ic_passed in (None, (), [], frozenset()), (
        f"garbage label leaked into infocategories: {ic_passed!r}"
    )


# -----------------------------------------------------------------------
# gap-5 regression — D-15b auto-commit on checkbox change with debounce
# See: .planning/phases/04-browse-tab-port/04-HUMAN-UAT.md gap-5
#      .planning/phases/04-browse-tab-port/04-CONTEXT.md D-15b
# (Apply button removed; gap-2/gap-3/gap-4 contracts superseded by D-15b.)
# -----------------------------------------------------------------------

def test_picker_checklist_carries_d15b_hx_attributes(client, monkeypatch):
    """gap-5 regression: each picker's <ul class="popover-search-list"> MUST
    carry hx-post="/browse/grid" + hx-target="#browse-grid" + hx-trigger
    containing "delay:250ms" so bubbling change events from inner checkboxes
    fire a single debounced commit per D-15b. The Apply button MUST be absent.

    This replaces the gap-2/gap-4 Apply-button assertions which were
    contractually superseded when the user requested removal of the Apply
    button (gap-5, 2026-04-28).
    """
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ])
    r = client.get("/browse")
    assert r.status_code == 200
    # Apply button MUST be gone (D-15b: there is no commit gesture).
    assert "popover-apply-btn" not in r.text, (
        "D-15b regression: popover-apply-btn class is back in the rendered "
        "page. The Apply button must be removed; auto-commit on change is "
        "the only commit path."
    )
    # popover-search-list MUST appear at least twice (Platforms + Parameters).
    assert r.text.count("popover-search-list") >= 2, (
        "D-15b regression: expected popover-search-list to appear >= 2 times "
        "(once per picker); got fewer."
    )
    # Each popover-search-list <ul> must carry the required hx-* attributes.
    # Anchor on the class and slice ~600 chars forward to capture the open
    # <ul ...> tag block.
    i = 0
    occurrences = 0
    while True:
        j = r.text.find("popover-search-list", i)
        if j == -1:
            break
        block = r.text[j : j + 600]
        assert 'hx-post="/browse/grid"' in block, (
            "D-15b regression: <ul class=\"popover-search-list\"> is missing "
            f"hx-post=\"/browse/grid\". Block: {block[:400]!r}"
        )
        assert 'hx-target="#browse-grid"' in block, (
            "D-15b regression: <ul class=\"popover-search-list\"> is missing "
            "hx-target=\"#browse-grid\"."
        )
        assert "delay:250ms" in block, (
            "D-15b regression: <ul class=\"popover-search-list\"> hx-trigger "
            "must contain \"delay:250ms\" so quick toggle bursts collapse to "
            "a single POST /browse/grid request. The original D-14 concern "
            "(5 toggles ≠ 5 queries) is addressed by HTMX's built-in "
            "delay: trigger modifier."
        )
        assert 'hx-include="#browse-filter-form"' in block, (
            "D-15b regression: <ul class=\"popover-search-list\"> missing "
            "hx-include=\"#browse-filter-form\". Without it, HTMX's "
            "getInputValues() iterates only direct <input> children of the "
            "<ul> and posts an empty body — the same failure mode as gap-2 "
            "before the fix. The form-element selector triggers HTMX's "
            "form.elements iteration, which includes form-associated "
            "checkboxes from BOTH pickers (cross-picker selection preserved)."
        )
        occurrences += 1
        i = j + 1
    assert occurrences >= 2, f"Expected >=2 popover-search-list occurrences; got {occurrences}"
    # Defense-in-depth: the gap-2 form-association on individual checkboxes
    # is still required (HTMX auto-includes form-associated inputs in the
    # POST body when the trigger element has hx-include="closest form" OR
    # when the bubble-source is a form-associated input via element.form).
    assert 'form="browse-filter-form"' in r.text, (
        "gap-2 regression (preserved under D-15b): checkboxes must still "
        "carry form=\"browse-filter-form\" so HTMX includes them in the "
        "POST body. This is a precondition; the auto-commit fires from the "
        "<ul> but the body must contain the checked values."
    )


def test_post_browse_grid_with_populated_payload_renders_grid(client, monkeypatch):
    """D-15b regression: the form body HTMX produces from the auto-commit
    checklist trigger (debounced change) renders the populated pivot grid.

    Under D-15b, when the user toggles checkboxes in either picker, the
    bubbling change events fire `hx-post=/browse/grid` on the <ul> after
    a 250ms debounce. HTMX's getInputValues() iterates form.elements of
    the form-associated <input type="checkbox"> elements (each carries
    form="browse-filter-form" — the gap-2 precondition that survives the
    Apply-button removal) and emits a body like:
        platforms=P1&platforms=P2&params=attribute%20%C2%B7%20vendor_id

    This test sends that body shape and asserts:
      - response is 200
      - response contains the populated pivot table (NOT the empty-state alert)
      - platforms+params arrived at fetch_cells as a non-empty tuple
    """
    captured: dict = {}

    def _capture_fetch(db, p, ic, i, row_cap=200, db_name=""):
        captured["platforms"] = p
        captured["infocategories"] = ic
        captured["items"] = i
        return (
            pd.DataFrame({
                "PLATFORM_ID": ["P1", "P2"],
                "InfoCategory": ["attribute", "attribute"],
                "Item": ["vendor_id", "vendor_id"],
                "Result": ["0xA1", "0xB2"],
            }),
            False,
        )

    _patch_cache(
        monkeypatch,
        platforms=["P1", "P2"],
        params=[{"InfoCategory": "attribute", "Item": "vendor_id"}],
        fetch=_capture_fetch,
    )

    r = _post_form_pairs(client, "/browse/grid", [
        ("platforms", "P1"),
        ("platforms", "P2"),
        ("params", "attribute · vendor_id"),
    ])
    assert r.status_code == 200

    # The populated grid renders — NOT the empty-state alert.
    assert "Select platforms and parameters above to build the pivot grid." not in r.text, (
        "gap-2 still open: Apply payload produced the empty-state alert. "
        "Either the form-association fix in _picker_popover.html was reverted, "
        "or the route handler regressed."
    )
    assert 'class="table table-striped table-hover table-sm pivot-table"' in r.text, (
        "Populated pivot table missing from /browse/grid response"
    )
    assert "0xA1" in r.text and "0xB2" in r.text, (
        "Pivot table cell values missing — fetch_cells return value did not reach the template"
    )

    # Affirmative invariant: fetch_cells received the actual selected values
    # (not an empty tuple). This proves the form body carried platforms+params,
    # which post-fix is what HTMX's element.form / form.elements path delivers.
    assert captured.get("platforms") == ("P1", "P2"), (
        f"fetch_cells received wrong platforms tuple: {captured.get('platforms')!r}"
    )
    assert captured.get("items") == ("vendor_id",), (
        f"fetch_cells received wrong items tuple: {captured.get('items')!r}"
    )


# -----------------------------------------------------------------------
# gap-3 regression — picker badge OOB swap on Apply (2026-04-28)
# See: .planning/phases/04-browse-tab-port/04-HUMAN-UAT.md gap-3
#      D-14(b) — Apply MUST update the trigger button's count badge
# -----------------------------------------------------------------------


def test_post_browse_grid_emits_picker_badge_oob_blocks(client, monkeypatch):
    """gap-3 regression: POST /browse/grid emits OOB picker badge updates.

    D-14(b): clicking Apply MUST update the trigger button's count badge.
    The badges live in .browse-filter-bar OUTSIDE #browse-grid, so they
    cannot be reached by the primary innerHTML swap on #browse-grid.
    Fix: the route emits a `picker_badges_oob` block alongside the grid,
    carrying two hx-swap-oob spans (one per picker) that HTMX merges by
    id into the persistent shell.

    This test sends a POST with non-empty platforms+params (2 platforms,
    1 param) and asserts:
      - Both `picker-platforms-badge` and `picker-params-badge` spans
        appear in the response
      - Each carries `hx-swap-oob="true"`
      - The text content of each equals the count of currently-selected
        items (2 for platforms, 1 for params)
      - The visibility class is NOT `d-none` (badges should be visible
        when count > 0 per D-08)
    """
    _patch_cache(monkeypatch, platforms=["P1", "P2"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ], fetch=lambda db, p, ic, i, row_cap=200, db_name="": (
        pd.DataFrame({
            "PLATFORM_ID": ["P1", "P2"],
            "InfoCategory": ["attribute", "attribute"],
            "Item": ["vendor_id", "vendor_id"],
            "Result": ["0xA1", "0xB2"],
        }), False,
    ))
    r = _post_form_pairs(client, "/browse/grid", [
        ("platforms", "P1"),
        ("platforms", "P2"),
        ("params", "attribute · vendor_id"),
    ])
    assert r.status_code == 200

    # Both badge OOB spans must appear in the response body.
    assert 'id="picker-platforms-badge"' in r.text, (
        "gap-3 regression: picker-platforms-badge OOB span missing from "
        "POST /browse/grid response. Apply will not update the platforms "
        "trigger badge — D-14(b) breached."
    )
    assert 'id="picker-params-badge"' in r.text, (
        "gap-3 regression: picker-params-badge OOB span missing from "
        "POST /browse/grid response. Apply will not update the params "
        "trigger badge — D-14(b) breached."
    )

    # Each badge must carry hx-swap-oob="true" (otherwise HTMX will not
    # merge it into the persistent shell — it would land inside #browse-grid
    # via the primary swap and immediately get wiped on the next swap).
    # Slice each badge's tag and confirm the OOB attribute.
    for badge_id, expected_count in [
        ("picker-platforms-badge", "2"),
        ("picker-params-badge", "1"),
    ]:
        i = r.text.index(f'id="{badge_id}"')
        tag_start = r.text.rfind("<span", 0, i)
        tag_end = r.text.find("</span>", i)
        assert tag_start != -1 and tag_end != -1, (
            f"could not locate <span>...</span> for {badge_id} in response"
        )
        tag = r.text[tag_start : tag_end + len("</span>")]
        assert 'hx-swap-oob="true"' in tag, (
            f"gap-3: {badge_id} missing hx-swap-oob — HTMX will not merge "
            f"it into the persistent shell. Got: {tag!r}"
        )
        # Text content equals the integer count.
        inner_start = tag.index(">", tag.index("<span")) + 1
        inner_end = tag.index("</span>")
        inner = tag[inner_start:inner_end].strip()
        assert inner == expected_count, (
            f"gap-3: {badge_id} text content is {inner!r}, "
            f"expected {expected_count!r} (count of selected items)"
        )
        # Non-empty selection — badge must NOT be hidden via d-none.
        assert "d-none" not in tag, (
            f"gap-3: {badge_id} carries d-none even though selection is "
            f"non-empty — D-08 visual contract breached. Tag: {tag!r}"
        )


def test_post_browse_grid_picker_badge_zero_count_renders_hidden(client, monkeypatch):
    """gap-3 regression: badge OOB still emits even when selection is empty.

    Why: HTMX needs a stable target to merge into. If the OOB block were
    conditional ({% if vm.selected_platforms %}<span>...</span>{% endif %}),
    the post-Apply round-trip from non-empty -> empty would NOT emit the
    OOB span, and the trigger badge would stay at the previous (stale)
    count instead of getting hidden.

    D-08 visual contract (no visible badge when empty) is preserved by
    toggling the `d-none` Bootstrap class on the always-emitted span,
    not by emit-or-omit.

    This test sends a POST with empty selection (Clear-all reset path —
    D-18) and asserts:
      - Both badge OOB spans STILL appear in the response (stable target)
      - Each carries `hx-swap-oob="true"`
      - The text content is "0" (the integer count, not omitted)
      - The class string contains `d-none` (visually hidden per D-08)
      - The empty-state alert renders in the grid block (sanity check
        that the empty-selection path still works post-fix)
    """
    def _no_call(*args, **kwargs):
        raise AssertionError(
            "fetch_cells must NOT be called when selection is empty"
        )
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ], fetch=_no_call)

    r = _post_form_pairs(client, "/browse/grid", [])
    assert r.status_code == 200

    # Empty-selection branch confirmed (sanity — empties the grid).
    assert (
        "Select platforms and parameters above to build the pivot grid."
        in r.text
    )

    # Both badge OOB spans MUST still emit — even though the selection is
    # empty. HTMX needs the stable target to merge "0" + d-none into the
    # persistent badges; without it, stale counts persist.
    for badge_id in ("picker-platforms-badge", "picker-params-badge"):
        assert f'id="{badge_id}"' in r.text, (
            f"gap-3 regression: {badge_id} missing from response when "
            f"selection is empty. The OOB block must ALWAYS emit so HTMX "
            f"has a stable swap target — otherwise non-empty -> empty "
            f"transitions leave the trigger badge stuck on the prior count."
        )
        i = r.text.index(f'id="{badge_id}"')
        tag_start = r.text.rfind("<span", 0, i)
        tag_end = r.text.find("</span>", i)
        tag = r.text[tag_start : tag_end + len("</span>")]
        assert 'hx-swap-oob="true"' in tag, (
            f"{badge_id} missing hx-swap-oob in empty-selection response: {tag!r}"
        )
        # Text content equals "0" (count).
        inner_start = tag.index(">", tag.index("<span")) + 1
        inner_end = tag.index("</span>")
        inner = tag[inner_start:inner_end].strip()
        assert inner == "0", (
            f"{badge_id} text content for empty selection is {inner!r}, "
            f"expected '0'"
        )
        # Visually hidden via d-none — D-08 contract.
        assert "d-none" in tag, (
            f"gap-3: {badge_id} for empty selection MUST carry d-none "
            f"(D-08: no visible badge when count is 0). Got: {tag!r}"
        )


