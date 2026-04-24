"""app_v2.services — v2.0-specific services (caching, content files, etc.).

Framework-agnostic v1.0 modules under app/services/ are imported directly by
v2.0 code (no copies). This package holds v2.0-only concerns: cachetools
wrappers, atomic file I/O for content pages, YAML persistence for the curated
overview list.
"""
