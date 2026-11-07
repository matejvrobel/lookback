import json
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError

from app.api.deps import SessionDep
from app.schemas.settings import SECTION_MODELS, AppSettings
from app.services.settings_store import settings_store

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettings)
async def get_settings() -> AppSettings:
    return settings_store.current


@router.get("/schema")
async def get_settings_schema() -> dict:
    return AppSettings.model_json_schema()


def _require_section(section: str) -> None:
    if section not in SECTION_MODELS:
        raise HTTPException(404, f"Unknown settings section: {section}")


@router.get("/{section}")
async def get_settings_section(section: str) -> dict:
    _require_section(section)
    return getattr(settings_store.current, section).model_dump(mode="json")


@router.delete("/{section}")
async def reset_settings_section(section: str, session: SessionDep) -> dict:
    _require_section(section)
    return (await settings_store.reset(session, section)).model_dump(mode="json")


@router.put("/{section}")
async def update_settings_section(
    section: str, session: SessionDep, values: dict[str, Any] = Body(...)
) -> dict:
    _require_section(section)
    try:
        updated = await settings_store.update(session, section, values)
    except ValidationError as exc:
        raise HTTPException(422, json.loads(exc.json(include_url=False))) from exc
    return updated.model_dump(mode="json")
