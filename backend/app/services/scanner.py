import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.config import get_env
from app.database import SessionLocal, utcnow
from app.models import Camera, Recording, ThumbStatus
from app.schemas.settings import AppSettings
from app.services import ffmpeg
from app.services.camera_matcher import CameraMatcher
from app.services.settings_store import settings_store
from app.services.thumbnails import remove_thumbnails
from app.services.timestamps import compile_patterns, local_day, parse_path_timestamp

log = logging.getLogger(__name__)

BATCH_SIZE = 100
SKIPPED_DIR_PREFIXES = (".", "@", "#")


@dataclass(slots=True)
class FileEntry:
    path: str
    root: str
    rel_path: str
    size: int
    mtime: float


@dataclass
class WalkResult:
    files: dict[str, FileEntry] = field(default_factory=dict)
    busy: set[str] = field(default_factory=set)
    available_roots: set[str] = field(default_factory=set)


@dataclass
class ScanStats:
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    files_seen: int = 0
    added: int = 0
    updated: int = 0
    removed: int = 0
    errors: int = 0
    unavailable_roots: list[str] = field(default_factory=list)


@dataclass
class IndexContext:
    matcher: CameraMatcher
    patterns: list
    tz: ZoneInfo
    settings: AppSettings
    semaphore: asyncio.Semaphore


def normalize_root(root: str) -> str:
    return os.path.normpath(root)


def walk_roots(roots: list[str], extensions: list[str], ignore_patterns: list[str], min_age: int) -> WalkResult:
    wanted = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}
    now = time.time()
    result = WalkResult()

    for root in map(normalize_root, roots):
        if not os.path.isdir(root):
            log.warning("Root folder %s is not available", root)
            continue
        found_any = False
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(SKIPPED_DIR_PREFIXES)]
            for name in filenames:
                if os.path.splitext(name)[1].lower() not in wanted:
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                if any(fnmatch(rel, pattern) for pattern in ignore_patterns):
                    continue
                try:
                    stat = os.stat(full)
                except OSError:
                    continue
                found_any = True
                if now - stat.st_mtime < min_age:
                    result.busy.add(full)
                    continue
                result.files[full] = FileEntry(full, root, rel, stat.st_size, stat.st_mtime)
        if found_any:
            result.available_roots.add(root)
    return result


class Scanner:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._scan_requested = False
        self.last_stats: ScanStats | None = None

    @property
    def running(self) -> bool:
        return self._scan_requested

    async def scan(self) -> ScanStats | None:
        if self._scan_requested:
            return None
        self._scan_requested = True
        try:
            async with self._lock:
                return await self._run_scan()
        finally:
            self._scan_requested = False

    async def _run_scan(self) -> ScanStats:
        stats = ScanStats()
        try:
            await self._scan(stats)
        except Exception:
            log.exception("Library scan failed")
            stats.errors += 1
        stats.finished_at = time.time()
        self.last_stats = stats
        log.info(
            "Scan finished in %.1fs: %d files, %d added, %d updated, %d removed, %d errors",
            stats.finished_at - stats.started_at,
            stats.files_seen,
            stats.added,
            stats.updated,
            stats.removed,
            stats.errors,
        )
        return stats

    async def _scan(self, stats: ScanStats) -> None:
        settings = settings_store.current
        library = settings.library
        walk = await asyncio.to_thread(
            walk_roots,
            library.root_folders,
            library.extensions,
            library.ignore_patterns,
            library.min_file_age_seconds,
        )
        stats.files_seen = len(walk.files)
        stats.unavailable_roots = [
            r for r in map(normalize_root, library.root_folders) if r not in walk.available_roots
        ]

        async with SessionLocal() as session:
            rows = await session.execute(
                select(Recording.id, Recording.path, Recording.size, Recording.mtime, Recording.root)
            )
            existing = {row.path: row for row in rows}
            cameras = (await session.scalars(select(Camera))).all()

        if library.remove_missing:
            missing = [
                row.id
                for path, row in existing.items()
                if path not in walk.files and path not in walk.busy and row.root in walk.available_roots
            ]
            await self._remove(missing)
            stats.removed = len(missing)

        changed = [
            entry
            for path, entry in walk.files.items()
            if (row := existing.get(path)) is None or row.size != entry.size or row.mtime != entry.mtime
        ]
        context = IndexContext(
            matcher=CameraMatcher(cameras),
            patterns=compile_patterns(library.timestamp_patterns),
            tz=ZoneInfo(settings.general.timezone),
            settings=settings,
            semaphore=asyncio.Semaphore(settings.scanner.probe_concurrency),
        )
        for offset in range(0, len(changed), BATCH_SIZE):
            batch = changed[offset : offset + BATCH_SIZE]
            rows_to_write = await asyncio.gather(*(self._build_row(entry, context) for entry in batch))
            await self._upsert(rows_to_write)
            for row in rows_to_write:
                if row["path"] in existing:
                    stats.updated += 1
                else:
                    stats.added += 1
                if row["probe_error"]:
                    stats.errors += 1

    async def _build_row(self, entry: FileEntry, ctx: IndexContext) -> dict[str, Any]:
        async with ctx.semaphore:
            probe = await ffmpeg.probe(entry.path, ctx.settings.ffmpeg.ffprobe_path)
            if not probe.duration and probe.error is None:
                probe.duration = await ffmpeg.measure_duration(entry.path, ctx.settings.ffmpeg.ffmpeg_path)

        rule = ctx.matcher.match(entry.rel_path)
        patterns = ([rule.timestamp_pattern] if rule and rule.timestamp_pattern else []) + ctx.patterns
        duration = probe.duration or 0.0

        start = parse_path_timestamp(entry.rel_path, patterns, ctx.tz)
        source = "filename"
        if start is None and probe.creation_time is not None:
            start, source = probe.creation_time, "metadata"
        if start is None:
            start, source = entry.mtime - duration, "mtime"

        return {
            "camera_id": rule.camera_id if rule else None,
            "path": entry.path,
            "root": entry.root,
            "rel_path": entry.rel_path,
            "size": entry.size,
            "mtime": entry.mtime,
            "start_ts": start,
            "end_ts": start + duration,
            "duration": duration,
            "day": local_day(start, ctx.tz),
            "timestamp_source": source,
            "container": Path(entry.path).suffix.lstrip(".").lower(),
            "video_codec": probe.video_codec,
            "audio_codec": probe.audio_codec,
            "width": probe.width,
            "height": probe.height,
            "fps": probe.fps,
            "probe_error": probe.error,
            "thumb_status": ThumbStatus.pending,
            "thumb_count": 0,
            "thumb_interval": None,
            "indexed_at": utcnow(),
        }

    async def _upsert(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        stmt = sqlite_insert(Recording).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Recording.path],
            set_={key: stmt.excluded[key] for key in rows[0] if key != "path"},
        )
        async with SessionLocal() as session:
            await session.execute(stmt)
            await session.commit()

    async def _remove(self, ids: list[int]) -> None:
        if not ids:
            return
        async with SessionLocal() as session:
            for offset in range(0, len(ids), 500):
                chunk = ids[offset : offset + 500]
                await session.execute(delete(Recording).where(Recording.id.in_(chunk)))
            await session.commit()
        remove_thumbnails(get_env().thumbs_dir, ids)

    async def rematch(self) -> int:
        async with self._lock:
            async with SessionLocal() as session:
                matcher = CameraMatcher((await session.scalars(select(Camera))).all())
                rows = await session.execute(select(Recording.id, Recording.rel_path, Recording.camera_id))
                changes = []
                for row in rows:
                    rule = matcher.match(row.rel_path)
                    camera_id = rule.camera_id if rule else None
                    if camera_id != row.camera_id:
                        changes.append({"id": row.id, "camera_id": camera_id})
                if changes:
                    await session.execute(update(Recording), changes)
                    await session.commit()
        log.info("Camera rematch updated %d recordings", len(changes))
        return len(changes)

    async def invalidate_all(self) -> None:
        async with self._lock:
            async with SessionLocal() as session:
                await session.execute(update(Recording).values(size=-1))
                await session.commit()
