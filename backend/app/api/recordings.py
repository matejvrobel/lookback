from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CameraIdsQuery, GroupIdQuery, RecordingDep, SessionDep, resolve_camera_filter
from app.models import Recording, ThumbStatus
from app.runtime import thumbnail_worker
from app.schemas.recording import AdjacentRecordings, RecordingOut, RecordingPage

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.get("", response_model=RecordingPage)
async def list_recordings(
    session: SessionDep,
    camera_ids: CameraIdsQuery = None,
    group_id: GroupIdQuery = None,
    unassigned: bool = False,
    start: float | None = Query(None, description="Unix timestamp, inclusive overlap"),
    end: float | None = Query(None, description="Unix timestamp, exclusive overlap"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> RecordingPage:
    stmt = select(Recording)
    if unassigned:
        stmt = stmt.where(Recording.camera_id.is_(None))
    elif (ids := await resolve_camera_filter(session, camera_ids, group_id)) is not None:
        stmt = stmt.where(Recording.camera_id.in_(ids))
    if start is not None:
        stmt = stmt.where(Recording.end_ts > start)
    if end is not None:
        stmt = stmt.where(Recording.start_ts < end)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    items = await session.scalars(stmt.order_by(Recording.start_ts.desc()).limit(limit).offset(offset))
    return RecordingPage(total=total or 0, items=[RecordingOut.model_validate(r) for r in items])


@router.get("/{recording_id}", response_model=RecordingOut)
async def get_recording(recording: RecordingDep) -> Recording:
    return recording


async def _neighbour(session: AsyncSession, recording: Recording, forward: bool) -> Recording | None:
    same_camera = (
        Recording.camera_id.is_(None) if recording.camera_id is None else Recording.camera_id == recording.camera_id
    )
    if forward:
        position = or_(
            Recording.start_ts > recording.start_ts,
            and_(Recording.start_ts == recording.start_ts, Recording.id > recording.id),
        )
        order = (Recording.start_ts.asc(), Recording.id.asc())
    else:
        position = or_(
            Recording.start_ts < recording.start_ts,
            and_(Recording.start_ts == recording.start_ts, Recording.id < recording.id),
        )
        order = (Recording.start_ts.desc(), Recording.id.desc())
    stmt = select(Recording).where(same_camera, position).order_by(*order).limit(1)
    return (await session.scalars(stmt)).first()


@router.get("/{recording_id}/adjacent", response_model=AdjacentRecordings)
async def adjacent_recordings(recording: RecordingDep, session: SessionDep) -> AdjacentRecordings:
    previous = await _neighbour(session, recording, forward=False)
    following = await _neighbour(session, recording, forward=True)
    return AdjacentRecordings(
        previous=RecordingOut.model_validate(previous) if previous else None,
        next=RecordingOut.model_validate(following) if following else None,
        gap_before=recording.start_ts - previous.end_ts if previous else None,
        gap_after=following.start_ts - recording.end_ts if following else None,
    )


def _image_response(recording: Recording, path: Path) -> FileResponse:
    if recording.thumb_status != ThumbStatus.done or not path.is_file():
        raise HTTPException(404, "Thumbnail not available yet")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{recording_id}/thumbnail.jpg")
async def recording_thumbnail(recording: RecordingDep) -> FileResponse:
    return _image_response(recording, thumbnail_worker.poster_path(recording.id))


@router.get("/{recording_id}/sprite.jpg")
async def recording_sprite(recording: RecordingDep) -> FileResponse:
    return _image_response(recording, thumbnail_worker.sprite_path(recording.id))
