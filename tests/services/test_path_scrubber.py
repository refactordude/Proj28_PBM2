"""Tests for app.services.path_scrubber — SAFE-06.

TDD RED phase: tests written before implementation exists.
Import will fail with ModuleNotFoundError until app/services/path_scrubber.py is created.

Covers:
  - /sys/ prefix replaced with <path>
  - /proc/ prefix replaced with <path>
  - /dev/ prefix replaced with <path>
  - Multiple occurrences in one string both replaced
  - Non-matching text passes through unchanged
  - /usr/bin/python NOT replaced (only sys/proc/dev match)
  - Empty string returns empty string
"""
from __future__ import annotations

import pytest

from app.services.path_scrubber import scrub_paths


class TestSysPathScrubbed:
    def test_sys_kernel_replaced(self):
        result = scrub_paths("/sys/kernel/foo")
        assert "<path>" in result
        assert "/sys/kernel" not in result

    def test_sys_path_standalone(self):
        result = scrub_paths("/sys/devices/platform")
        assert result == "<path>"


class TestProcPathScrubbed:
    def test_proc_cpuinfo_replaced(self):
        result = scrub_paths("/proc/cpuinfo")
        assert "<path>" in result
        assert "/proc/cpuinfo" not in result

    def test_proc_self_replaced(self):
        result = scrub_paths("/proc/self/status")
        assert "<path>" in result


class TestDevPathScrubbed:
    def test_dev_sda_replaced(self):
        result = scrub_paths("/dev/sda1")
        assert "<path>" in result
        assert "/dev/sda" not in result

    def test_dev_null_replaced(self):
        """Even /dev/null must be scrubbed per D-26."""
        result = scrub_paths("/dev/null")
        assert result == "<path>"


class TestMultipleOccurrences:
    def test_both_sys_and_proc_replaced(self):
        text = "value=/sys/kernel/foo and /proc/cpuinfo"
        result = scrub_paths(text)
        assert result.count("<path>") == 2
        assert "/sys/" not in result
        assert "/proc/" not in result

    def test_three_occurrences(self):
        text = "/sys/a /proc/b /dev/c"
        result = scrub_paths(text)
        assert result.count("<path>") == 3


class TestUppercasePathsScrubbed:
    def test_uppercase_sys_scrubbed(self):
        """/SYS/ uppercase variant must be scrubbed (re.IGNORECASE) — WR-03 regression."""
        result = scrub_paths("/SYS/BLOCK/sda")
        assert "<path>" in result
        assert "/SYS/" not in result

    def test_uppercase_proc_scrubbed(self):
        result = scrub_paths("/PROC/cpuinfo")
        assert "<path>" in result
        assert "/PROC/" not in result

    def test_uppercase_dev_scrubbed(self):
        result = scrub_paths("/DEV/null")
        assert "<path>" in result
        assert "/DEV/" not in result

    def test_mixed_case_sys_scrubbed(self):
        result = scrub_paths("/Sys/kernel/foo")
        assert "<path>" in result


class TestNonMatchingPassthrough:
    def test_plain_text_unchanged(self):
        text = "plain text with no paths"
        assert scrub_paths(text) == text

    def test_usr_bin_not_scrubbed(self):
        """Only /sys/, /proc/, /dev/ match — /usr/ must pass through."""
        text = "path /usr/bin/python"
        assert scrub_paths(text) == text

    def test_empty_string_returns_empty(self):
        assert scrub_paths("") == ""
