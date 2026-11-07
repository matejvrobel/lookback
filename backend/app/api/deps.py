from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import CameraGroup, Recording

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CameraIdsQuery = Annotated[list[int] | None, Query(description="Repeatable camera id filter")]
GroupIdQuery = Annotated[int | None, Query(description="Camera group id filter")]


async def get_recording(recording_id: int, session: SessionDep) -> Recording:
    recording = await session.get(Recording, recording_id)
    if recording is None:
        raise HTTPException(404, "Recording not found")
    return recording


RecordingDep = Annotated[Recording, Depends(get_recording)]


async def resolve_camera_filter(
    session: AsyncSession, camera_ids: list[int] | None, group_id: int | None
) -> list[int] | None:
    if group_id is None:
        return camera_ids or None
    group = await session.get(CameraGroup, group_id)
    if group is None:
        raise HTTPException(404, "Camera group not found")
    return sorted({camera.id for camera in group.cameras} | set(camera_ids or []))
