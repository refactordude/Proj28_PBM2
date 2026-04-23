"""
Unit tests for app.services.result_normalizer (Plan 01-02, DATA-01..04).

TDD RED phase — all tests in this file must fail until the implementation module
is created (app/services/result_normalizer.py does not exist yet).

Coverage:
  DATA-01: is_missing / normalize — missing sentinels and shell-error prefixes
  DATA-02: classify — 8 result types, no coercion side effects
  DATA-03: split_lun_item — LUN index 0..7 prefix parsing
  DATA-04: split_dme_suffix / unpack_dme_compound — DME side detection + compound value
  Stage 5: try_numeric — on-demand hex/decimal coercion
"""
import pandas as pd
import pytest

from app.services import result_normalizer as rn


# ---------------------------------------------------------------------------
# DATA-01: is_missing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("val", [
    None,
    "",
    "   ",           # whitespace-only after strip
    "None",          # Pitfall 4 — the string "None" must be treated as missing
    "null",
    "NULL",
    "N/A",
    "N/a",
])
def test_is_missing_returns_true_for_known_sentinels(val):
    assert rn.is_missing(val) is True


def test_is_missing_handles_python_None():
    assert rn.is_missing(None) is True


def test_is_missing_handles_empty_string():
    assert rn.is_missing("") is True


def test_is_missing_handles_whitespace_only_string():
    assert rn.is_missing("   ") is True


def test_is_missing_handles_None_string():
    """Pitfall 4: the literal string 'None' is NOT a valid value — it is missing."""
    assert rn.is_missing("None") is True


def test_is_missing_handles_shell_error_cat_prefix():
    assert rn.is_missing("cat: /sys/block/sda/foo: No such file or directory") is True


def test_is_missing_handles_shell_error_permission_denied():
    assert rn.is_missing("Permission denied") is True


def test_is_missing_handles_shell_error_no_such_file():
    assert rn.is_missing("No such file or directory") is True


def test_is_missing_returns_false_for_hex_value():
    assert rn.is_missing("0x1F") is False


def test_is_missing_returns_false_for_valid_identifier():
    assert rn.is_missing("actual_value") is False


def test_is_missing_returns_false_for_decimal_string():
    assert rn.is_missing("42") is False


def test_is_missing_returns_false_for_nonempty_csv():
    assert rn.is_missing("a,b,c") is False


def test_is_missing_returns_false_for_compound_value():
    assert rn.is_missing("local=0,peer=1") is False


# ---------------------------------------------------------------------------
# DATA-01: normalize
# ---------------------------------------------------------------------------

def test_normalize_converts_None_sentinel_to_pd_NA():
    s = rn.normalize(pd.Series(["None", "0x1F", "", "cat: missing"]))
    assert pd.isna(s.iloc[0])
    assert not pd.isna(s.iloc[1])
    assert pd.isna(s.iloc[2])
    assert pd.isna(s.iloc[3])


def test_normalize_returns_hex_value_unchanged():
    s = rn.normalize(pd.Series(["0x1F"]))
    assert s.iloc[0] == "0x1F"


def test_normalize_converts_python_None_to_pd_NA():
    s = rn.normalize(pd.Series([None, "0xFF"]))
    assert pd.isna(s.iloc[0])


def test_normalize_converts_shell_error_to_pd_NA():
    s = rn.normalize(pd.Series(["cat: /sys/block/sda/foo: No such file or directory"]))
    assert pd.isna(s.iloc[0])


def test_normalize_converts_permission_denied_to_pd_NA():
    s = rn.normalize(pd.Series(["Permission denied"]))
    assert pd.isna(s.iloc[0])


# ---------------------------------------------------------------------------
# DATA-02: classify — no coercion
# ---------------------------------------------------------------------------

def test_classify_None_is_MISSING():
    assert rn.classify(None) == rn.ResultType.MISSING


def test_classify_empty_string_is_MISSING():
    assert rn.classify("") == rn.ResultType.MISSING


def test_classify_cat_shell_error_is_ERROR():
    assert rn.classify("cat: /sys/foo") == rn.ResultType.ERROR


def test_classify_lowercase_hex_is_HEX():
    assert rn.classify("0x1F") == rn.ResultType.HEX


def test_classify_uppercase_hex_prefix_is_HEX():
    assert rn.classify("0XFF") == rn.ResultType.HEX


def test_classify_plain_integer_is_DECIMAL():
    assert rn.classify("42") == rn.ResultType.DECIMAL


def test_classify_negative_decimal_is_DECIMAL():
    assert rn.classify("-3.14") == rn.ResultType.DECIMAL


def test_classify_scientific_notation_is_DECIMAL():
    assert rn.classify("1.2e-3") == rn.ResultType.DECIMAL


def test_classify_comma_list_without_equals_is_CSV():
    assert rn.classify("a,b,c") == rn.ResultType.CSV


def test_classify_key_value_pairs_is_COMPOUND():
    assert rn.classify("local=0,peer=1") == rn.ResultType.COMPOUND


def test_classify_multiline_string_is_WHITESPACE_BLOB():
    assert rn.classify("line1\nline2\nline3") == rn.ResultType.WHITESPACE_BLOB


def test_classify_plain_identifier_is_IDENTIFIER():
    assert rn.classify("sda") == rn.ResultType.IDENTIFIER


def test_classify_samsung_brand_is_IDENTIFIER():
    assert rn.classify("SAMSUNG") == rn.ResultType.IDENTIFIER


def test_classify_does_not_coerce_hex_string():
    """DATA-02: classify must return enum without mutating / converting the input."""
    original = "0x1F"
    result = rn.classify(original)
    # Result must be the HEX enum member
    assert result == rn.ResultType.HEX
    # The string itself should NOT have been converted to int
    assert isinstance(original, str)
    assert original == "0x1F"


def test_classify_returns_enum_member_not_raw_value():
    """classify must return a ResultType member, not a plain string."""
    result = rn.classify("42")
    assert isinstance(result, rn.ResultType)


# ---------------------------------------------------------------------------
# DATA-03: split_lun_item
# ---------------------------------------------------------------------------

def test_split_lun_item_parses_lun_0_prefix():
    assert rn.split_lun_item("0_WriteProt") == (0, "WriteProt")


def test_split_lun_item_parses_lun_7_prefix():
    assert rn.split_lun_item("7_WriteProt") == (7, "WriteProt")


def test_split_lun_item_parses_lun_3_prefix():
    assert rn.split_lun_item("3_WriteProt") == (3, "WriteProt")


def test_split_lun_item_rejects_out_of_range_8():
    """LUN index must be 0..7; 8 is out of range."""
    assert rn.split_lun_item("8_WriteProt") == (None, "8_WriteProt")


def test_split_lun_item_rejects_double_digit_prefix():
    """Two-digit numbers like 12 are NOT valid LUN indices."""
    assert rn.split_lun_item("12_foo") == (None, "12_foo")


def test_split_lun_item_returns_None_for_no_prefix():
    assert rn.split_lun_item("WriteProt") == (None, "WriteProt")


def test_split_lun_item_handles_field_with_underscore():
    """Items like '3_Block_Size' should return (3, 'Block_Size')."""
    result = rn.split_lun_item("3_Block_Size")
    assert result == (3, "Block_Size")


# ---------------------------------------------------------------------------
# DATA-04: split_dme_suffix
# ---------------------------------------------------------------------------

def test_split_dme_suffix_detects_local_side():
    assert rn.split_dme_suffix("attr_local") == ("attr", "local")


def test_split_dme_suffix_detects_peer_side():
    assert rn.split_dme_suffix("attr_peer") == ("attr", "peer")


def test_split_dme_suffix_returns_None_for_no_side():
    assert rn.split_dme_suffix("attr") == ("attr", None)


def test_split_dme_suffix_handles_multi_part_base_with_local():
    assert rn.split_dme_suffix("foo_bar_local") == ("foo_bar", "local")


def test_split_dme_suffix_handles_multi_part_base_with_peer():
    assert rn.split_dme_suffix("foo_bar_peer") == ("foo_bar", "peer")


def test_split_dme_suffix_no_match_returns_original():
    """If no _local/_peer suffix, return (original, None)."""
    assert rn.split_dme_suffix("sda") == ("sda", None)


# ---------------------------------------------------------------------------
# DATA-04: unpack_dme_compound
# ---------------------------------------------------------------------------

def test_unpack_dme_compound_parses_local_peer_decimal():
    assert rn.unpack_dme_compound("local=0,peer=1") == {"local": "0", "peer": "1"}


def test_unpack_dme_compound_parses_local_peer_hex():
    assert rn.unpack_dme_compound("local=0x1F,peer=0x20") == {
        "local": "0x1F",
        "peer": "0x20",
    }


def test_unpack_dme_compound_returns_empty_dict_for_no_equals():
    assert rn.unpack_dme_compound("abc") == {}


def test_unpack_dme_compound_returns_empty_dict_for_empty_string():
    assert rn.unpack_dme_compound("") == {}


def test_unpack_dme_compound_handles_single_key():
    result = rn.unpack_dme_compound("key=val")
    assert result == {"key": "val"}


# ---------------------------------------------------------------------------
# Stage 5: try_numeric
# ---------------------------------------------------------------------------

def test_try_numeric_converts_hex_to_int():
    result = rn.try_numeric(pd.Series(["0x1F"]))
    assert result.iloc[0] == 31


def test_try_numeric_converts_plain_integer():
    result = rn.try_numeric(pd.Series(["42"]))
    assert result.iloc[0] == 42.0


def test_try_numeric_converts_float():
    result = rn.try_numeric(pd.Series(["3.14"]))
    assert result.iloc[0] == pytest.approx(3.14)


def test_try_numeric_returns_pd_NA_for_non_numeric_string():
    result = rn.try_numeric(pd.Series(["abc"]))
    assert pd.isna(result.iloc[0])


def test_try_numeric_handles_None_as_NA():
    result = rn.try_numeric(pd.Series([None, "0x1F"]))
    assert pd.isna(result.iloc[0])
    assert result.iloc[1] == 31


def test_try_numeric_handles_existing_pd_NA():
    result = rn.try_numeric(pd.Series([pd.NA, "3.14"]))
    assert pd.isna(result.iloc[0])
    assert result.iloc[1] == pytest.approx(3.14)


def test_try_numeric_handles_mixed_series():
    result = rn.try_numeric(pd.Series(["0x10", "abc", "2.5"]))
    assert result.iloc[0] == 16
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pytest.approx(2.5)
