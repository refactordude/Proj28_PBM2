"""Tests for app.services.ollama_fallback — NL-09.

TDD RED phase: tests written before implementation exists.
Import will fail with ModuleNotFoundError until app/services/ollama_fallback.py is created.

Covers three fallback stages:
  Stage 1 — clean JSON direct parse
  Stage 2 — markdown code fence stripping (```json ... ``` and ``` ... ```)
  Stage 3 — regex first { ... } block extraction (DOTALL)
  Failure — all stages fail → return None

Additional:
  - Nested dict
  - Empty string → None
"""
from __future__ import annotations

import pytest

from app.services.ollama_fallback import extract_json


class TestStage1CleanJson:
    def test_clean_json_object(self):
        result = extract_json('{"a": 1}')
        assert result == {"a": 1}

    def test_clean_json_nested(self):
        result = extract_json('{"a": {"b": 2, "c": [1, 2]}}')
        assert result == {"a": {"b": 2, "c": [1, 2]}}

    def test_clean_json_multikey(self):
        result = extract_json('{"query": "SELECT 1", "explanation": "returns one"}')
        assert result == {"query": "SELECT 1", "explanation": "returns one"}


class TestStage2MarkdownFence:
    def test_json_fenced_with_language_tag(self):
        raw = '```json\n{"a": 1}\n```'
        result = extract_json(raw)
        assert result == {"a": 1}

    def test_json_fenced_without_language_tag(self):
        raw = '```\n{"a": 1}\n```'
        result = extract_json(raw)
        assert result == {"a": 1}

    def test_json_fenced_with_extra_whitespace(self):
        raw = '```json\n  {"a": 1}  \n```'
        result = extract_json(raw)
        assert result == {"a": 1}


class TestStage3EmbeddedBrace:
    def test_prose_before_json(self):
        raw = 'Sure, here is the JSON: {"a": 1} hope that helps'
        result = extract_json(raw)
        assert result == {"a": 1}

    def test_multiline_json_embedded(self):
        raw = 'chat says:\n{"a":\n1}\ngoodbye'
        result = extract_json(raw)
        assert result == {"a": 1}

    def test_nested_json_embedded(self):
        raw = 'Here you go: {"query": "SELECT *", "explanation": "all rows"}'
        result = extract_json(raw)
        assert result == {"query": "SELECT *", "explanation": "all rows"}


class TestAllFallbacksFail:
    def test_plain_text_no_json(self):
        result = extract_json("no json here at all")
        assert result is None

    def test_empty_string(self):
        result = extract_json("")
        assert result is None

    def test_only_array_not_dict(self):
        """extract_json must return None for a JSON array (not a dict)."""
        result = extract_json("[1, 2, 3]")
        assert result is None

    def test_malformed_json(self):
        result = extract_json("{not valid json at all}")
        assert result is None
