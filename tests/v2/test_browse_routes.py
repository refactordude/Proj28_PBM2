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
    # for one platform; pivot_to_wide_core (real, not mocked) caps at 30.
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
# gap-2 regression — Apply button form-association (2026-04-27)
# See: .planning/debug/gap-2-apply-no-swap.md
#      .planning/phases/04-browse-tab-port/04-HUMAN-UAT.md gap-2
# -----------------------------------------------------------------------

def test_apply_button_carries_form_attribute(client, monkeypatch):
    """gap-2 regression: Apply submit button MUST carry form="browse-filter-form".

    This is the contract that lets HTMX's dn()/Nt() auto-include the
    empty <form id="browse-filter-form"> for non-GET requests, which in
    turn iterates form.elements (browser DOM API) — picking up every
    form-associated checkbox in the picker dropdowns even though they
    are NOT DOM descendants of the form.

    Before the fix: the button used hx-include="#browse-filter-form input:checked",
    a CSS descendant selector that matched zero elements. POST body was
    empty -> empty-state alert. See .planning/debug/gap-2-apply-no-swap.md.
    """
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "attribute", "Item": "vendor_id"},
    ])
    r = client.get("/browse")
    assert r.status_code == 200
    # The popover-apply-btn class is the unique selector for the Apply button
    assert "popover-apply-btn" in r.text, "Apply button missing from rendered popover"
    # Locate the Apply button block and confirm form= attribute is present
    # within it. Use the class as the anchor and slice ~600 chars forward
    # (the button block is ~10 lines including the hx-* attributes).
    i = r.text.index("popover-apply-btn")
    block = r.text[i : i + 600]
    assert 'form="browse-filter-form"' in block, (
        "gap-2 regression: Apply button is missing form=\"browse-filter-form\". "
        "Without it, HTMX cannot auto-include the picker checkboxes in the "
        "POST /browse/grid body and the grid will not swap on Apply click. "
        f"Got block: {block[:400]!r}"
    )
    # Defense-in-depth: the broken pre-fix hx-include selector must be gone.
    # If it returns, the bug is back even if form= is also present.
    assert 'hx-include="#browse-filter-form input:checked"' not in block, (
        "gap-2 regression: the broken hx-include CSS-descendant selector "
        "is back on the Apply button. Remove it — form= attribute is sufficient."
    )


def test_post_browse_grid_apply_button_payload_renders_populated_grid(client, monkeypatch):
    """gap-2 regression: the form body that HTMX produces post-fix renders the grid.

    Post-fix, when the user clicks Apply, HTMX's dn() function:
      1. resolves Nt(applyButton) = applyButton.form (= the empty
         #browse-filter-form, courtesy of the new form= attribute)
      2. fn() iterates form.elements (which includes the form-associated
         checkboxes inside the dropdown menus via the form= attr they
         ALREADY have on the <input type="checkbox"> elements)
      3. emits a POST body like:
             platforms=P1&platforms=P2&params=attribute%20%C2%B7%20vendor_id

    This test sends exactly that body and asserts:
      - response is 200
      - response contains the populated pivot table (NOT the empty-state alert)
      - the platforms+params arrived at fetch_cells as a non-empty tuple
        (proves the form-association actually carried the values, not that
        the route handler accidentally tolerated the empty body).

    Before the fix the same Apply click sent platforms=&params= (or rather,
    no keys at all) -> is_empty_selection=True -> empty-state alert.
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
