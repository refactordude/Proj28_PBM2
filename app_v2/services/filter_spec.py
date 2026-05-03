"""Phase 4 — UI Foundation: FilterGroup / FilterOption view-models (D-UIF-04).

Pydantic v2 models passed to the `filters_popover` macro in
`app_v2/templates/_components/filters_popover.html`. Driven from
routers that want chip-group multi-category filtering on a page.
Distinct from `_picker_popover.html`'s checkbox-list contract
(D-UI2-09 byte-stable; the two primitives coexist).

Researcher recommendation (RESEARCH.md Open Question 2): live in a
separate file from hero_spec.py for cleaner imports — mirrors the
one-concept-per-file convention in services/.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FilterOption(BaseModel):
    """One toggleable chip in a filter group.

    `value` must be a non-empty string (WR-04 fix). Empty-string values
    are ambiguous on the wire: the chip-toggle.js OFF state already
    excludes the hidden input from form submission via the `disabled`
    attribute, but a chip whose ON-state value was '' would still be
    indistinguishable from "no value submitted" on the server. Reject
    empty values at construction time so the bug cannot reach the DOM.
    """

    label: str
    value: str = Field(min_length=1)
    on: bool = False


class FilterGroup(BaseModel):
    """A labelled row of toggleable chip options.

    Used as `groups=[FilterGroup(label="Status", options=[FilterOption(...)])]`
    in the filters_popover macro call.
    """

    label: str
    options: list[FilterOption] = Field(default_factory=list)
