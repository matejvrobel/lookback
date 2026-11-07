import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SettingsSection
from app.schemas.settings import SECTION_MODELS, AppSettings

log = logging.getLogger(__name__)

Listener = Callable[[str, AppSettings, AppSettings], Awaitable[None]]


class SettingsStore:
    def __init__(self) -> None:
        self._current = AppSettings()
        self._listeners: list[Listener] = []

    @property
    def current(self) -> AppSettings:
        return self._current

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    async def load(self, session: AsyncSession) -> None:
        sections: dict[str, BaseModel] = {}
        for row in (await session.scalars(select(SettingsSection))).all():
            model = SECTION_MODELS.get(row.section)
            if model is None:
                continue
            try:
                sections[row.section] = model.model_validate(row.data)
            except ValidationError:
                log.warning("Stored settings for section %r are invalid, using defaults", row.section)
        self._current = AppSettings(**sections)

    async def update(self, session: AsyncSession, section: str, values: dict[str, Any]) -> BaseModel:
        model = SECTION_MODELS[section]
        merged = getattr(self._current, section).model_dump() | values
        validated = model.model_validate(merged)

        await session.merge(SettingsSection(section=section, data=validated.model_dump(mode="json")))
        await session.commit()
        await self._apply(section, validated)
        return validated

    async def reset(self, session: AsyncSession, section: str) -> BaseModel:
        defaults = SECTION_MODELS[section]()
        await session.execute(delete(SettingsSection).where(SettingsSection.section == section))
        await session.commit()
        await self._apply(section, defaults)
        return defaults

    async def _apply(self, section: str, value: BaseModel) -> None:
        previous = self._current
        self._current = previous.model_copy(update={section: value})
        for listener in self._listeners:
            try:
                await listener(section, previous, self._current)
            except Exception:
                log.exception("Settings listener failed for section %r", section)


settings_store = SettingsStore()
