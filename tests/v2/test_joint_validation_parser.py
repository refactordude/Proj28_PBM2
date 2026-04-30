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
