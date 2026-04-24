"""Jinja2 template loader for app_v2 — wrapped with jinja2_fragments for HTMX
partial rendering (Phase 2+ uses block_name= to render template blocks).

CRITICAL: all TemplateResponse calls use the Starlette 1.0 signature
`templates.TemplateResponse(request, name, context_dict)` — request is the FIRST
positional argument, NOT inside the context dict. The old
TemplateResponse(name, {"request": request, ...}) form raises TypeError in
Starlette 1.0 (shipped with FastAPI 0.136.x).
"""
from pathlib import Path

from jinja2_fragments.fastapi import Jinja2Blocks

TEMPLATE_DIR = Path(__file__).parent

templates = Jinja2Blocks(directory=str(TEMPLATE_DIR))
