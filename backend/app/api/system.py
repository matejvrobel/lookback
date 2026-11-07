from dataclasses import asdict

from fastapi import APIRouter
from sqlalchemy import func, select

from app import __version__
from app.api.deps import SessionDep
from app.models import Camera, Recording, ThumbStatus
from app.runtime import scanner, task_manager
from app.services import ffmpeg
from app.services.settings_store import settings_store

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/status")
async def status(session: SessionDep) -> dict:
    recordings = await session.scalar(select(func.count()).select_from(Recording))
    unassigned = await session.scalar(select(func.count()).where(Recording.camera_id.is_(None)))
    pending_thumbs = await session.scalar(
        select(func.count()).where(Recording.thumb_status == ThumbStatus.pending)
    )
    cameras = await session.scalar(select(func.count()).select_from(Camera))
    return {
        "version": __version__,
        "ffmpeg": await ffmpeg.version(settings_store.current.ffmpeg.ffmpeg_path),
        "recordings": recordings,
        "unassigned_recordings": unassigned,
        "pending_thumbnails": pending_thumbs,
        "cameras": cameras,
        "scanner": {
            "running": scanner.running,
            "interval_minutes": settings_store.current.scanner.interval_minutes,
            "next_scan_at": task_manager.next_scan_at,
            "last_scan": asdict(scanner.last_stats) if scanner.last_stats else None,
        },
    }


@router.post("/scan", status_code=202)
async def start_scan() -> dict:
    return {"started": task_manager.trigger_scan()}


@router.post("/rematch")
async def rematch_cameras() -> dict:
    return {"changed": await scanner.rematch()}
