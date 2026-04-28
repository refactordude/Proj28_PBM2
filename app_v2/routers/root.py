"""Root full-page routes (currently empty — overview owns /, browse owns
/browse, ask owns /ask after Phase 6).

Phase 6 D-22 / Plan 06-03: GET /ask stub removed; the new ask router at
``app_v2/routers/ask.py`` owns the /ask URL. This module retains an empty
APIRouter only so ``app_v2/main.py``'s import + include_router still link.

INFRA-05 convention: any future routes added here MUST be ``def``, not
``async def``, even if they don't touch the DB — establishing the convention
prevents accidental ``async def`` later when DB calls arrive.
"""
from fastapi import APIRouter

router = APIRouter()
