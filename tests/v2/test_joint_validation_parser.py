"""Tests for app_v2/services/joint_validation_parser.py — D-JV-04, D-JV-05."""
from __future__ import annotations

from pathlib import Path

import pytest

from app_v2.services.joint_validation_parser import (
    ParsedJV,
    _extract_label_value,
    _extract_link,
    parse_index_html,
)
from bs4 import BeautifulSoup


FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def primary_html_bytes() -> bytes:
    return (FIXTURE_DIR / "joint_validation_sample.html").read_bytes()


@pytest.fixture
def fallback_html_bytes() -> bytes:
    return (FIXTURE_DIR / "joint_validation_fallback_sample.html").read_bytes()


def test_parse_primary_shape_all_13_fields(primary_html_bytes: bytes) -> None:
    parsed = parse_index_html(primary_html_bytes)
    assert parsed.title == "Samsung S22 Ultra UFS 3.1 Joint Validation"
    assert parsed.status == "In Progress"
    assert parsed.customer == "Samsung"
    assert parsed.model_name == "S22Ultra"
    assert parsed.ap_company == "Qualcomm"
    assert parsed.ap_model == "SM8450"
    assert parsed.device == "UFS 3.1"
    assert parsed.controller == "FW v2.3"
    assert parsed.application == "Smartphone"
    assert parsed.assignee == "홍길동"
    assert parsed.start == "2026-03-15"
    assert parsed.end == "2026-06-30"
    assert parsed.link == "https://confluence.example.com/pages/3193868109"


def test_parse_fallback_shape_p_strong_colon(fallback_html_bytes: bytes) -> None:
    parsed = parse_index_html(fallback_html_bytes)
    assert parsed.title == "Sparse Fixture"
    assert parsed.customer == "TestCustomer"
    assert parsed.model_name == "TestModel"
    assert parsed.assignee == "김철수"
    assert parsed.start == "2026-04-01"
    # D-JV-05 — missing field → blank "", NOT em-dash, NOT None
    assert parsed.status == ""
    assert parsed.ap_company == ""


def test_parse_missing_h1_returns_blank_title() -> None:
    html = b"<html><body><p>no h1</p></body></html>"
    assert parse_index_html(html).title == ""


def test_parse_korean_label_byte_equal() -> None:
    html = b"<table><tr><th><strong>\xeb\x8b\xb4\xeb\x8b\xb9\xec\x9e\x90</strong></th><td>\xea\xb9\x80\xec\xb2\xa0\xec\x88\x98</td></tr></table>"
    parsed = parse_index_html(html)
    assert parsed.assignee == "김철수"


def test_parse_first_match_wins_on_duplicate_label() -> None:
    html = (
        b"<table><tr><th><strong>Status</strong></th><td>First</td></tr>"
        b"<tr><th><strong>Status</strong></th><td>Second</td></tr></table>"
    )
    assert parse_index_html(html).status == "First"


def test_parse_empty_value_cell_returns_blank() -> None:
    html = b"<table><tr><th><strong>Customer</strong></th><td></td></tr></table>"
    assert parse_index_html(html).customer == ""


def test_parse_link_extracts_first_anchor_href() -> None:
    html = (
        b"<table><tr><th><strong>Report Link</strong></th>"
        b'<td><a href="https://example.com/page">Link Text</a></td></tr></table>'
    )
    assert parse_index_html(html).link == "https://example.com/page"


def test_parse_label_in_anchor_walks_up_correctly() -> None:
    html = (
        b'<table><tr><th><a href="#"><strong>Status</strong></a></th>'
        b"<td>OK</td></tr></table>"
    )
    assert parse_index_html(html).status == "OK"


def test_parse_strong_with_surrounding_whitespace() -> None:
    html = b"<table><tr><th><strong>  Customer  </strong></th><td>Acme</td></tr></table>"
    assert parse_index_html(html).customer == "Acme"


def test_parse_returns_plain_str_not_navigablestring(primary_html_bytes: bytes) -> None:
    parsed = parse_index_html(primary_html_bytes)
    for field in ("title", "status", "customer", "model_name", "ap_company",
                  "ap_model", "device", "controller", "application",
                  "assignee", "start", "end", "link"):
        value = getattr(parsed, field)
        assert type(value) is str, f"{field} is {type(value).__name__}, expected str"


def test_parse_page_properties_with_wrapped_value() -> None:
    # Real Confluence Page Properties macro shape: <strong> wrapped in
    # <p> inside <td>; value lives in next-sibling <td> wrapped in
    # <div class="content-wrapper"><p>...</p></div>.
    html = (
        b"<table><tbody>"
        b"<tr><td><p><strong>Status</strong></p></td>"
        b'<td><div class="content-wrapper"><p>Planned</p></div></td></tr>'
        b"<tr><td><p><strong>Customer</strong></p></td>"
        b"<td><p>Acme Corp</p></td></tr>"
        b"<tr><td><strong>Device</strong></td>"
        b"<td>UFS 4.0</td></tr>"
        b"</tbody></table>"
    )
    parsed = parse_index_html(html)
    assert parsed.status == "Planned"
    assert parsed.customer == "Acme Corp"
    assert parsed.device == "UFS 4.0"


def test_parse_prefers_page_properties_over_heading_for_duplicate_label() -> None:
    # Same field label in BOTH a standalone heading (no value beside it)
    # AND a Page Properties row. The table row MUST win.
    html = (
        b"<html><body>"
        b"<h1><strong>Status</strong></h1>"   # heading-only — no usable value
        b"<table><tbody>"
        b"<tr><td><p><strong>Status</strong></p></td>"
        b"<td><p>Planned</p></td></tr>"
        b"</tbody></table>"
        b"</body></html>"
    )
    assert parse_index_html(html).status == "Planned"


def test_parse_strips_parens_from_start_and_end_only() -> None:
    # Start/End: leading "(" + trailing ")" → strip; idempotent on bare value.
    # Inline-paragraph shape:
    html_inline = (
        b"<html><body>"
        b"<h1>X</h1>"
        b"<p><strong>Start</strong>: (2024-03-01)</p>"
        b"<p><strong>End</strong>: 2024-09-30</p>"   # bare — must stay bare
        b"</body></html>"
    )
    parsed = parse_index_html(html_inline)
    assert parsed.start == "2024-03-01"
    assert parsed.end == "2024-09-30"

    # Page-Properties shape with parens:
    html_pp = (
        b"<table><tbody>"
        b"<tr><td><p><strong>Start</strong></p></td>"
        b"<td><p>(2024-03-01)</p></td></tr>"
        b"<tr><td><p><strong>End</strong></p></td>"
        b"<td><p>(2024-09-30)</p></td></tr>"
        b"</tbody></table>"
    )
    parsed_pp = parse_index_html(html_pp)
    assert parsed_pp.start == "2024-03-01"
    assert parsed_pp.end == "2024-09-30"


def test_parse_paren_strip_does_not_apply_to_other_fields() -> None:
    # Customer: "Acme (lead)" is a legitimate value — parens MUST stay.
    html = (
        b"<table><tbody>"
        b"<tr><th><strong>Customer</strong></th><td>Acme (lead)</td></tr>"
        b"<tr><th><strong>AP Model</strong></th><td>(SM8650)</td></tr>"
        b"</tbody></table>"
    )
    parsed = parse_index_html(html)
    assert parsed.customer == "Acme (lead)"
    assert parsed.ap_model == "(SM8650)"   # parens preserved on non-Start/End fields


def test_parse_skips_strong_inside_h1_for_status() -> None:
    # Real-export bug class: <strong>Status</strong> appears inside an
    # <h1> heading (page title or section header) AND the canonical metadata
    # lives in a Page-Properties row below. The heading-nested <strong>
    # MUST be skipped so the Page-Properties row wins.
    # 260507-lox: skip generalized to all fields (not Status-specific) —
    # a label inside a heading is never the canonical metadata source.
    html = (
        b"<html><body>"
        b"<h1><strong>Status</strong>: leaked-from-heading</h1>"
        b"<table><tbody>"
        b"<tr><td><p><strong>Status</strong></p></td>"
        b"<td><p>Planned</p></td></tr>"
        b"</tbody></table>"
        b"</body></html>"
    )
    assert parse_index_html(html).status == "Planned"


def test_parse_skips_strong_inside_h2_for_customer_generalization() -> None:
    # Generalization proof: the same h1-h6 skip applies to other fields
    # (here Customer in <h2>), NOT just Status. Confirms the bug-class fix
    # is universal — see 260507-lox plan rationale.
    html = (
        b"<html><body>"
        b"<h2><strong>Customer</strong>: Acme HQ</h2>"
        b"<table><tbody>"
        b"<tr><td><strong>Customer</strong></td>"
        b"<td>Beta Inc.</td></tr>"
        b"</tbody></table>"
        b"</body></html>"
    )
    assert parse_index_html(html).customer == "Beta Inc."
