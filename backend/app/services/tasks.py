import asyncio
import logging
import os
import time
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

from app.schemas.settings import AppSettings
from app.services.playback import HlsManager, RemuxCache, prune_cache
from app.services.scanner import ScanStats, Scanner
from app.services.settings_store import settings_store
from app.services.thumbnails import ThumbnailWorker

log = logging.getLogger(__name__)

JANITOR_INTERVAL_SECONDS = 60


class TaskManager:
    """Owns every long-running background loop of the application."""

    def __init__(self, scanner: Scanner, thumbnails: ThumbnailWorker, remux: RemuxCache, hls: HlsManager) -> None:
        self.scanner = scanner
        self.thumbnails = thumbnails
        self.remux = remux
        self.hls = hls
        self._loops: list[asyncio.Task] = []
        self._background: set[asyncio.Task] = set()
        self._watch_task: asyncio.Task | None = None
        self._delayed_scan: asyncio.Task | None = None
        self._reschedule = asyncio.Event()
        self.next_scan_at: float | None = None

    async def start(self) -> None:
        settings_store.subscribe(self._on_settings_changed)
        self._loops = [
            asyncio.create_task(self._scan_loop(), name="scan-loop"),
            asyncio.create_task(self.thumbnails.run(), name="thumbnails"),
            asyncio.create_task(self._janitor_loop(), name="cache-janitor"),
        ]
        self._restart_watcher()

    async def stop(self) -> None:
        tasks = [*self._loops, *self._background, self._watch_task, self._delayed_scan]
        for task in filter(None, tasks):
            task.cancel()
        await asyncio.gather(*filter(None, tasks), return_exceptions=True)
        await self.hls.shutdown()

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._background.add(task)
        task.add_done_callback(self._on_background_done)
        return task

    def _on_background_done(self, task: asyncio.Task) -> None:
        self._background.discard(task)
        if not task.cancelled() and task.exception():
            log.error("Background task failed", exc_info=task.exception())

    async def run_scan(self) -> ScanStats | None:
        stats = await self.scanner.scan()
        if stats and (stats.added or stats.updated):
            self.thumbnails.wake()
        return stats

    def trigger_scan(self) -> bool:
        if self.scanner.running:
            return False
        self.spawn(self.run_scan())
        return True

    def _schedule_delayed_scan(self, delay: float) -> None:
        if self._delayed_scan and not self._delayed_scan.done():
            self._delayed_scan.cancel()

        async def _later() -> None:
            await asyncio.sleep(delay)
            await self.run_scan()

        self._delayed_scan = asyncio.create_task(_later())

    async def _scan_loop(self) -> None:
        if settings_store.current.scanner.scan_on_startup:
            await self.run_scan()
        while True:
            interval = settings_store.current.scanner.interval_minutes * 60
            self.next_scan_at = time.time() + interval if interval else None
            self._reschedule.clear()
            try:
                await asyncio.wait_for(self._reschedule.wait(), timeout=interval or None)
            except asyncio.TimeoutError:
                self.next_scan_at = None
                await self.run_scan()

    async def _watch_loop(self, roots: list[str], settings: AppSettings) -> None:
        from watchfiles import awatch

        extensions = tuple(ext.lower() for ext in settings.library.extensions)
        delay = settings.library.min_file_age_seconds + 2
        log.info("Watching %s for changes", ", ".join(roots))
        async for changes in awatch(*roots, force_polling=settings.scanner.watch_force_polling):
            if any(path.lower().endswith(extensions) for _, path in changes):
                self._schedule_delayed_scan(delay)

    def _restart_watcher(self) -> None:
        if self._watch_task:
            self._watch_task.cancel()
            self._watch_task = None
        settings = settings_store.current
        if not settings.scanner.watch_enabled:
            return
        roots = [root for root in settings.library.root_folders if os.path.isdir(root)]
        if roots:
            self._watch_task = asyncio.create_task(self._watch_loop(roots, settings), name="file-watcher")

    async def _janitor_loop(self) -> None:
        while True:
            await asyncio.sleep(JANITOR_INTERVAL_SECONDS)
            try:
                playback = settings_store.current.playback
                await self.hls.reap_idle(playback.hls_idle_timeout_seconds)
                directories: list[Path] = [self.remux.directory, self.hls.directory]
                removed = await asyncio.to_thread(
                    prune_cache, directories, playback.cache_size_mb * 1024 * 1024, self.hls.active_dirs()
                )
                if removed:
                    log.info("Pruned %d cached playback entries", removed)
            except Exception:
                log.exception("Cache janitor failed")

    async def _on_settings_changed(self, section: str, previous: AppSettings, current: AppSettings) -> None:
        if section in ("scanner", "library"):
            self._reschedule.set()
            self._restart_watcher()

        timezone_changed = previous.general.timezone != current.general.timezone
        patterns_changed = previous.library.timestamp_patterns != current.library.timestamp_patterns
        if timezone_changed or patterns_changed:
            log.info("Timestamp-related settings changed, re-indexing the whole library")
            await self.scanner.invalidate_all()
            self.trigger_scan()
