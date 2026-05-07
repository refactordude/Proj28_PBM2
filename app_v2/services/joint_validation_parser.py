"""BeautifulSoup4 13-field extraction from Confluence-exported index.html.

Implements D-JV-04: parse <h1> for title + <strong>Field</strong> rows for 12
metadata fields. First match wins on duplicate labels. Missing fields → blank
empty string "" (D-JV-05).

Two structural shapes are handled:
  1. Page Properties macro:  <tr><th><strong>Field</strong></th><td>value</td></tr>
  2. Inline paragraph:       <p><strong>Field</strong>: value</p>

Korean label `담당자` is matched byte-equal (U+B2F4 U+B2F9 U+C790).
"""
from __future__ import annotations

from typing import Final

from bs4 import BeautifulSoup
from pydantic import BaseModel


class ParsedJV(BaseModel):
    """13-field extraction result. All fields default to '' per D-JV-05."""
    title: str = ""
    status: str = ""
    customer: str = ""
    model_name: str = ""
    ap_company: str = ""
    ap_model: str = ""
    device: str = ""
    controller: str = ""
    application: str = ""
    assignee: str = ""    # 담당자
    start: str = ""       # YYYY-MM-DD or raw string
    end: str = ""         # YYYY-MM-DD or raw string
    link: str = ""        # Raw href; sanitized later in grid_service


_FIELD_LABELS: Final[dict[str, str]] = {
    "status": "Status",
    "customer": "Customer",
    "model_name": "Model Name",
    "ap_company": "AP Company",
    "ap_model": "AP Model",
    "device": "Device",
    "controller": "Controller",
    "application": "Application",
    "assignee": "담당자",
    "start": "Start",
    "end": "End",
}


def _strip_parens(value: str) -> str:
    """Strip a single matching pair of leading "(" + trailing ")".

    Safe-by-design: only strips when BOTH endpoints are present and the
    parens are at the very edges of the (already-trimmed) string.
    Idempotent on values without parens. Used ONLY for Start/End fields
    — applying it elsewhere would corrupt legitimate values like
    "Acme (lead)".
    """
    if len(value) >= 2 and value.startswith("(") and value.endswith(")"):
        return value[1:-1].strip()
    return value


def _extract_label_value(soup: BeautifulSoup, label: str) -> str:
    """Return trimmed text of the cell adjacent to <strong>label</strong>.

    Resolution order:
      1. Page Properties shape (preferred): <strong> sits inside a <th>/<td>
         cell (possibly wrapped in <p>, <a>, etc.). Walk up to the nearest
         <th>/<td> ancestor; the value lives in the next-sibling <th>/<td>.
         Tolerates wrappers in the value cell (<div class="content-wrapper">,
         <p>, nested combos) — full-text-strip is sufficient.
      2. Inline-paragraph fallback: <p><strong>label</strong>: value</p>.
         Same paragraph carries label and value separated by ":".

    Disambiguation: when the same <strong>label</strong> appears in
    MULTIPLE places (e.g. <h1> AND a Page Properties row), prefer the
    first match that produces a non-empty Page-Properties value over any
    heading-only match. Falls through to the inline-paragraph shape only
    if no Page-Properties match anywhere yields a non-empty value.
    """
    matches = soup.find_all(
        "strong",
        string=lambda s: s is not None and s.strip() == label,
    )
    if not matches:
        return ""
    inline_fallback = ""
    for strong in matches:
        # 260507-lox: skip <strong> whose nearest ancestor is <h1>..<h6>.
        # A label inside a heading is never the canonical metadata source —
        # it is a section title or page heading. Generalized skip (not
        # Status-specific): the bug class is universal — Customer / AP
        # Company / etc. would suffer the same shape in different exports.
        if strong.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"]) is not None:
            continue
        # Pass 1: prefer the Page-Properties shape — find the nearest
        # <th>/<td> ancestor and read its next-sibling cell's full text.
        cell = strong.find_parent(["th", "td"])
        if cell is not None:
            sibling = cell.find_next_sibling(["td", "th"])
            if sibling is not None:
                value = str(sibling.get_text(strip=True))
                if value:
                    return value
                # Empty value cell — preserved by existing
                # test_parse_empty_value_cell_returns_blank. Honour the
                # "first match wins on duplicate labels" rule WITHIN the
                # Page-Properties shape: stop scanning further matches.
                return ""
            # No sibling — keep scanning later matches.
            continue
        # Pass 2 candidate: <p><strong>label</strong>: value</p> shape.
        # Record the FIRST inline-paragraph candidate but keep scanning
        # — a later Page-Properties match should still win.
        if not inline_fallback:
            p_parent = strong.find_parent("p")
            if p_parent is not None:
                full = p_parent.get_text(strip=True)
                if full.startswith(label):
                    rest = full[len(label):].lstrip()
                    if rest.startswith(":"):
                        rest = rest[1:].lstrip()
                    inline_fallback = str(rest)
                else:
                    inline_fallback = str(full)
    return inline_fallback


def _extract_link(soup: BeautifulSoup) -> str:
    """First <a href=...> inside the cell adjacent to <strong>Report Link</strong>.

    Walks up to the nearest <th>/<td> ancestor of the matching <strong>
    (mirrors _extract_label_value Pass 1). Inline-paragraph fallback:
    if the strong sits directly in a <p>, search that <p> for an <a>.
    Returns raw href; sanitization happens later in grid_service.
    """
    matches = soup.find_all(
        "strong",
        string=lambda s: s is not None and s.strip() == "Report Link",
    )
    for strong in matches:
        # 260507-lox: skip <strong> whose nearest ancestor is <h1>..<h6>.
        # Mirror parity with _extract_label_value — a Report Link nested
        # inside a heading is not the canonical link source.
        if strong.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"]) is not None:
            continue
        cell = strong.find_parent(["th", "td"])
        if cell is not None:
            sibling = cell.find_next_sibling(["td", "th"])
            if sibling is None:
                continue
            a = sibling.find("a", href=True)
            if a is not None:
                return str(a["href"]).strip()
            continue
        # Inline-paragraph fallback.
        p_parent = strong.find_parent("p")
        if p_parent is not None:
            a = p_parent.find("a", href=True)
            if a is not None:
                return str(a["href"]).strip()
    return ""


def parse_index_html(html_bytes: bytes) -> ParsedJV:
    """Best-effort extraction. Failures → blank fields.

    Uses lxml backend by preference; falls back to html.parser if lxml is
    missing at runtime (defensive — lxml is a hard dependency, but the
    fallback keeps tests resilient if the wheel ever fails to install).
    """
    try:
        soup = BeautifulSoup(html_bytes, "lxml")
    except Exception:  # noqa: BLE001 — bs4 raises FeatureNotFound for missing parser
        soup = BeautifulSoup(html_bytes, "html.parser")
    h1 = soup.find("h1")
    title = str(h1.get_text(strip=True)) if h1 else ""
    return ParsedJV(
        title=title,
        status=_extract_label_value(soup, "Status"),
        customer=_extract_label_value(soup, "Customer"),
        model_name=_extract_label_value(soup, "Model Name"),
        ap_company=_extract_label_value(soup, "AP Company"),
        ap_model=_extract_label_value(soup, "AP Model"),
        device=_extract_label_value(soup, "Device"),
        controller=_extract_label_value(soup, "Controller"),
        application=_extract_label_value(soup, "Application"),
        assignee=_extract_label_value(soup, "담당자"),
        start=_strip_parens(_extract_label_value(soup, "Start")),
        end=_strip_parens(_extract_label_value(soup, "End")),
        link=_extract_link(soup),
    )
