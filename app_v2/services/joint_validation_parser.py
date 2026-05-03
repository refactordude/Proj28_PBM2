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


def _extract_label_value(soup: BeautifulSoup, label: str) -> str:
    """Return trimmed text of the cell adjacent to <strong>label</strong>.

    Handles BOTH the Page Properties shape and the <p><strong>...</strong>: ...</p>
    fallback. First match wins. Missing → "".
    """
    strong = soup.find(
        "strong",
        string=lambda s: s is not None and s.strip() == label,
    )
    if strong is None:
        return ""
    cell = strong.find_parent(["th", "td", "p"])
    if cell is None:
        return ""
    if cell.name in ("th", "td"):
        sibling = cell.find_next_sibling(["td", "th"])
        if sibling is None:
            return ""
        return str(sibling.get_text(strip=True))
    # cell.name == 'p' — fallback shape
    full = cell.get_text(strip=True)
    if full.startswith(label):
        rest = full[len(label):].lstrip()
        if rest.startswith(":"):
            rest = rest[1:].lstrip()
        return str(rest)
    return str(full)


def _extract_link(soup: BeautifulSoup) -> str:
    """First <a href=...> inside the cell adjacent to <strong>Report Link</strong>.

    Returns raw href; sanitization happens later in grid_service via _sanitize_link.
    """
    strong = soup.find(
        "strong",
        string=lambda s: s is not None and s.strip() == "Report Link",
    )
    if strong is None:
        return ""
    parent = strong.find_parent(["th", "td", "p"])
    if parent is None:
        return ""
    if parent.name in ("th", "td"):
        sibling = parent.find_next_sibling(["td", "th"])
    else:
        sibling = parent
    if sibling is None:
        return ""
    a = sibling.find("a", href=True)
    return str(a["href"]).strip() if a else ""


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
        start=_extract_label_value(soup, "Start"),
        end=_extract_label_value(soup, "End"),
        link=_extract_link(soup),
    )
