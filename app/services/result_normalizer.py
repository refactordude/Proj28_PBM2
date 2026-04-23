"""
Result normalization pipeline for ufs_data.Result field values.

5-stage pipeline:
  Stage 1: Missing sentinel detection (is_missing)
  Stage 2: Error string detection + classification (normalize, classify)
  Stage 3: LUN item prefix split on demand (split_lun_item)
  Stage 4: DME suffix split + compound value unpack on demand (split_dme_suffix, unpack_dme_compound)
  Stage 5: Lazy numeric coercion for chart/analysis only (try_numeric)

Public API (stable — imported by ufs_service in Plan 03):
  ResultType (Enum)
  MISSING_SENTINELS (frozenset)
  SHELL_ERROR_PREFIXES (tuple)
  is_missing(val) -> bool
  normalize(series: pd.Series) -> pd.Series
  classify(val) -> ResultType
  split_lun_item(item: str) -> tuple[int | None, str]
  split_dme_suffix(item: str) -> tuple[str, str | None]
  unpack_dme_compound(val: str) -> dict[str, str]
  try_numeric(series: pd.Series) -> pd.Series

Security note (T-02-01): classify uses anchored regexes (^...$) to prevent
classification bypass by embedded content. try_numeric wraps coercion in
try/except to contain ValueError from malformed strings.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Constants (DATA-01) — pin exactly as specified in plan
# ---------------------------------------------------------------------------

MISSING_SENTINELS: frozenset = frozenset({
    None, "None", "", "N/A", "N/a", "null", "NULL",
})

SHELL_ERROR_PREFIXES: tuple = (
    "cat: ",
    "Permission denied",
    "No such file",
)

# Pre-compiled regexes for classify (T-02-01: anchored to prevent bypass)
_HEX_RE = re.compile(r"^0[xX][0-9a-fA-F]+$")
_DECIMAL_RE = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")
_MULTI_SPACE_RE = re.compile(r"\s{2,}")

# Pre-compiled regex for split_lun_item (DATA-03)
# Match single digit 0-7 followed by underscore and at least one char
_LUN_PREFIX_RE = re.compile(r"^([0-7])_(.+)$")


# ---------------------------------------------------------------------------
# Stage 1: Missing sentinel detection (DATA-01)
# ---------------------------------------------------------------------------

class ResultType(Enum):
    MISSING = "missing"
    ERROR = "error"
    HEX = "hex"
    DECIMAL = "decimal"
    CSV = "csv"
    WHITESPACE_BLOB = "whitespace_blob"
    COMPOUND = "compound"
    IDENTIFIER = "identifier"


def is_missing(val: Any) -> bool:
    """Stage 1 — return True if val is a known missing sentinel or shell error string.

    Sentinel set (case-sensitive except for the explicit variants listed):
      None, "", "   " (whitespace-only), "None", "null", "NULL", "N/A", "N/a"
    Shell-error prefixes (case-sensitive):
      "cat: ", "Permission denied", "No such file"

    NOTE: "none" (all-lowercase) is NOT in the sentinel set per DATA-01.
    Type coercion never happens here — the return value is bool only.
    """
    # Handle None, float('nan'), np.nan, and pd.NA — all produced by pandas 3.x
    # StringDtype when None/pd.NA appears in a Series passed through .apply()
    if val is None:
        return True
    try:
        if pd.isna(val):
            return True
    except (TypeError, ValueError):
        pass  # pd.isna raises on array-like values; ignore
    if not isinstance(val, str):
        return False
    stripped = val.strip()
    # Whitespace-only or exact sentinel match
    if stripped in MISSING_SENTINELS:
        return True
    # Shell error prefix check
    if any(stripped.startswith(prefix) for prefix in SHELL_ERROR_PREFIXES):
        return True
    return False


# ---------------------------------------------------------------------------
# Stage 2: normalize + classify (DATA-01, DATA-02)
# ---------------------------------------------------------------------------

def normalize(series: pd.Series) -> pd.Series:
    """Stages 1-2: replace missing/error values with pd.NA; strip valid strings.

    Stages 3-4 (LUN split, DME split) are on-demand — call split_lun_item /
    split_dme_suffix separately when needed, not as part of the main pipeline.

    Returns a pd.Series with dtype=object where missing cells are pd.NA and
    valid cells are stripped strings. Pandas 3.x compatible (uses pd.NA).
    """
    def _norm(val: Any) -> Any:
        if is_missing(val):
            return pd.NA
        s = str(val).strip()
        if any(s.startswith(prefix) for prefix in SHELL_ERROR_PREFIXES):
            return pd.NA
        return s

    return series.apply(_norm)


def classify(val: Any) -> ResultType:
    """Stage 2: classify a Result value into a ResultType enum member.

    Heuristic order (important — do not reorder):
      1. MISSING  — is_missing(val) is True
      2. ERROR    — stripped string starts with a SHELL_ERROR_PREFIXES element
      3. HEX      — matches ^0[xX][0-9a-fA-F]+$
      4. DECIMAL  — matches ^-?\\d+(\\.\\d+)?([eE][-+]?\\d+)?$
      5. COMPOUND — contains both '=' and ','
      6. CSV      — contains ',' but no '='
      7. WHITESPACE_BLOB — contains '\\n' OR (len > 40 AND 2+ consecutive spaces)
      8. IDENTIFIER — fallback

    CONTRACT: this function never coerces val. It only reads val to determine
    the type; the caller's reference to val is unchanged after this call.
    Return type is always a ResultType member.

    Note on ordering: ERROR is checked before MISSING so that shell-error strings
    (e.g. "cat: /sys/foo") are returned as ERROR rather than MISSING, even though
    is_missing() also returns True for them. This lets callers distinguish between
    "no data" (MISSING) and "command failed" (ERROR) when they need that granularity.
    normalize() maps both to pd.NA regardless.
    """
    # Step 1: check for non-None/non-NA but string values that are shell errors
    # before the generic is_missing check, so they return ERROR not MISSING.
    if val is not None:
        try:
            _is_na = pd.isna(val)
        except (TypeError, ValueError):
            _is_na = False
        if not _is_na and isinstance(val, str):
            s_early = val.strip()
            if any(s_early.startswith(prefix) for prefix in SHELL_ERROR_PREFIXES):
                return ResultType.ERROR

    # Step 2: MISSING (None, nan, pd.NA, empty string, sentinel strings)
    if is_missing(val):
        return ResultType.MISSING

    s = str(val).strip()

    # Step 3 (was 2): ERROR (shell error prefix) — redundant guard kept for safety
    if any(s.startswith(prefix) for prefix in SHELL_ERROR_PREFIXES):
        return ResultType.ERROR

    # Step 3: HEX
    if _HEX_RE.match(s):
        return ResultType.HEX

    # Step 4: DECIMAL
    if _DECIMAL_RE.match(s):
        return ResultType.DECIMAL

    # Step 5: COMPOUND (has both '=' and ',')
    if "=" in s and "," in s:
        return ResultType.COMPOUND

    # Step 6: CSV (has ',' but no '=')
    if "," in s:
        return ResultType.CSV

    # Step 7: WHITESPACE_BLOB (multiline OR long string with multiple spaces)
    if "\n" in s or (len(s) > 40 and bool(_MULTI_SPACE_RE.search(s))):
        return ResultType.WHITESPACE_BLOB

    # Step 8: IDENTIFIER (fallback)
    return ResultType.IDENTIFIER


# ---------------------------------------------------------------------------
# Stage 3: LUN item prefix parsing (DATA-03)
# ---------------------------------------------------------------------------

def split_lun_item(item: str) -> tuple[int | None, str]:
    """Parse a LUN-prefixed Item name of the form 'N_fieldname' where N ∈ {0..7}.

    Returns:
      (lun_index: int, field_name: str)  — if item matches the pattern
      (None, item)                        — if item does not match (no prefix,
                                           out-of-range digit, double-digit, etc.)

    Examples:
      split_lun_item("0_WriteProt")  -> (0, "WriteProt")
      split_lun_item("7_WriteProt")  -> (7, "WriteProt")
      split_lun_item("8_WriteProt")  -> (None, "8_WriteProt")  # out of 0..7
      split_lun_item("12_foo")       -> (None, "12_foo")       # two-digit
      split_lun_item("WriteProt")    -> (None, "WriteProt")    # no prefix
    """
    m = _LUN_PREFIX_RE.match(item)
    if m:
        return (int(m.group(1)), m.group(2))
    return (None, item)


# ---------------------------------------------------------------------------
# Stage 4: DME suffix parsing and compound value unpacking (DATA-04)
# ---------------------------------------------------------------------------

def split_dme_suffix(item: str) -> tuple[str, str | None]:
    """Detect the DME side suffix (_local or _peer) in an Item name.

    Returns:
      (base_name: str, side: str)   — if item ends with '_local' or '_peer'
      (item, None)                  — otherwise (including empty string)

    Examples:
      split_dme_suffix("attr_local")      -> ("attr", "local")
      split_dme_suffix("attr_peer")       -> ("attr", "peer")
      split_dme_suffix("attr")            -> ("attr", None)
      split_dme_suffix("foo_bar_local")   -> ("foo_bar", "local")
      split_dme_suffix("")                -> ("", None)
    """
    if item.endswith("_local"):
        return (item[:-6], "local")
    if item.endswith("_peer"):
        return (item[:-5], "peer")
    return (item, None)


def unpack_dme_compound(val: str) -> dict[str, str]:
    """Unpack a DME compound value of the form 'key=val,key=val,...'.

    Returns a dict mapping each key to its raw string value. Malformed pieces
    (those without '=') are silently ignored.

    Returns {} if val is not a string, is empty, or contains no '=' character.

    Examples:
      unpack_dme_compound("local=0,peer=1")         -> {"local": "0", "peer": "1"}
      unpack_dme_compound("local=0x1F,peer=0x20")   -> {"local": "0x1F", "peer": "0x20"}
      unpack_dme_compound("abc")                    -> {}
      unpack_dme_compound("")                       -> {}
    """
    if not isinstance(val, str) or "=" not in val:
        return {}
    result: dict[str, str] = {}
    for piece in val.split(","):
        piece = piece.strip()
        if "=" in piece:
            k, _, v = piece.partition("=")
            result[k.strip()] = v.strip()
    return result


# ---------------------------------------------------------------------------
# Stage 5: Lazy numeric coercion for chart/analysis path only (DATA-02, VIZ-02)
# ---------------------------------------------------------------------------

def try_numeric(series: pd.Series) -> pd.Series:
    """Stage 5 — per-element coercion: hex string -> int, decimal string -> float.

    Used ONLY on the chart path (VIZ-02); never called as part of the main
    normalize() pipeline. Type coercion is lazy and per-query per DATA-02.

    Coercion rules:
      - pd.NA / None  -> pd.NA  (pass-through)
      - hex string    -> int (via int(s, 16))
      - decimal/float string -> float (via float(s))
      - anything else -> pd.NA  (ValueError caught)

    Return dtype is object (mixed int/float/pd.NA). Caller should not assume a
    homogeneous numeric dtype — use pd.to_numeric(..., errors='coerce') if a
    uniform float64 column is needed for Plotly.

    Security note (T-02-01): ValueError from malformed strings is caught and
    converted to pd.NA; no exception propagates to the caller.
    """
    def _coerce(val: Any) -> Any:
        if pd.isna(val):
            return pd.NA
        s = str(val).strip()
        if _HEX_RE.match(s):
            try:
                return int(s, 16)
            except ValueError:
                return pd.NA
        try:
            return float(s)
        except ValueError:
            return pd.NA

    return series.apply(_coerce)
