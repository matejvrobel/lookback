import asyncio
import logging
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sqlalchemy import select, update

from app.database import SessionLocal
from app.models import Recording, ThumbStatus
from app.schemas.settings import FFmpegSettings, ThumbnailSettings
from app.services import ffmpeg
from app.services.settings_store import settings_store

log = logging.getLogger(__name__)

BATCH_SIZE = 20
IDLE_WAIT_SECONDS = 300


def poster_path(directory: Path, recording_id: int) -> Path:
    return directory / f"{recording_id}.jpg"


def sprite_path(directory: Path, recording_id: int) -> Path:
    return directory / f"{recording_id}_sprite.jpg"


def remove_thumbnails(directory: Path, recording_ids: Iterable[int]) -> None:
    for recording_id in recording_ids:
        poster_path(directory, recording_id).unlink(missing_ok=True)
        sprite_path(directory, recording_id).unlink(missing_ok=True)


class ThumbnailWorker:
    """Builds a poster frame and a horizontal hover sprite for every recording, newest first."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._wake = asyncio.Event()

    def poster_path(self, recording_id: int) -> Path:
        return poster_path(self.directory, recording_id)

    def sprite_path(self, recording_id: int) -> Path:
        return sprite_path(self.directory, recording_id)

    def wake(self) -> None:
        self._wake.set()

    async def run(self) -> None:
        while True:
            processed = 0
            config = settings_store.current.thumbnails
            if config.enabled:
                try:
                    processed = await self._process_batch(config, settings_store.current.ffmpeg)
                except Exception:
                    log.exception("Thumbnail batch failed")
            if not processed:
                self._wake.clear()
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=IDLE_WAIT_SECONDS)
                except asyncio.TimeoutError:
                    pass

    async def _process_batch(self, config: ThumbnailSettings, ff: FFmpegSettings) -> int:
        async with SessionLocal() as session:
            recordings = (
                await session.scalars(
                    select(Recording)
                    .where(Recording.thumb_status == ThumbStatus.pending, Recording.duration > 0)
                    .order_by(Recording.start_ts.desc())
                    .limit(BATCH_SIZE)
                )
            ).all()
        if not recordings:
            return 0

        semaphore = asyncio.Semaphore(config.concurrency)
        results = await asyncio.gather(*(self._generate(r, config, ff, semaphore) for r in recordings))
        async with SessionLocal() as session:
            for values in results:
                recording_id = values.pop("id")
                await session.execute(update(Recording).where(Recording.id == recording_id).values(**values))
            await session.commit()
        return len(recordings)

    async def _generate(
        self, recording: Recording, config: ThumbnailSettings, ff: FFmpegSettings, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        interval = max(float(config.interval_seconds), recording.duration / config.max_per_clip)
        count = max(1, math.ceil(recording.duration / interval))
        sprite_error = None

        async with semaphore:
            error = await ffmpeg.generate_thumbnail(
                ff.ffmpeg_path,
                recording.path,
                self.poster_path(recording.id),
                min(1.0, recording.duration / 2),
                config.poster_width,
                config.quality,
            )
            if error is None:
                sprite_error = await ffmpeg.generate_sprite(
                    ff.ffmpeg_path,
                    recording.path,
                    self.sprite_path(recording.id),
                    interval,
                    count,
                    config.sprite_width,
                    config.quality,
                )

        if error is not None:
            log.warning("Thumbnail failed for %s: %s", recording.path, error)
            return {"id": recording.id, "thumb_status": ThumbStatus.failed}
        if sprite_error is not None:
            log.warning("Sprite failed for %s: %s", recording.path, sprite_error)
            count = 0
        return {"id": recording.id, "thumb_status": ThumbStatus.done, "thumb_count": count, "thumb_interval": interval}
