import json

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.models import Camera, Recording
from app.runtime import scanner
from app.schemas.camera import CameraBase, CameraCreate, CameraOut, CameraUpdate, MatchTestRequest, MatchTestResult
from app.services.camera_matcher import CameraMatcher

router = APIRouter(prefix="/cameras", tags=["cameras"])


async def _get_camera(session: SessionDep, camera_id: int) -> Camera:
    camera = await session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(404, "Camera not found")
    return camera


async def _commit(session: SessionDep) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "A camera with this name already exists") from exc


@router.get("", response_model=list[CameraOut])
async def list_cameras(session: SessionDep) -> list[CameraOut]:
    counts = dict(
        (await session.execute(select(Recording.camera_id, func.count()).group_by(Recording.camera_id))).all()
    )
    cameras = (await session.scalars(select(Camera).order_by(Camera.sort_order, Camera.name))).all()
    return [
        CameraOut.model_validate(camera).model_copy(update={"recording_count": counts.get(camera.id, 0)})
        for camera in cameras
    ]


@router.post("", response_model=CameraOut, status_code=201)
async def create_camera(payload: CameraCreate, session: SessionDep, background: BackgroundTasks) -> Camera:
    camera = Camera(**payload.model_dump())
    session.add(camera)
    await _commit(session)
    background.add_task(scanner.rematch)
    return camera


@router.post("/test-match", response_model=MatchTestResult)
async def test_match(payload: MatchTestRequest, session: SessionDep) -> MatchTestResult:
    probe = Camera(id=0, name="test", match_type=payload.match_type, match_value=payload.match_value, priority=0, enabled=True)
    matcher = CameraMatcher([probe])
    if not matcher.rules:
        raise HTTPException(422, "Invalid match expression")
    matched = [path for path in await session.scalars(select(Recording.rel_path)) if matcher.match(path)]
    return MatchTestResult(matched=len(matched), samples=matched[:20])


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(camera_id: int, session: SessionDep) -> Camera:
    return await _get_camera(session, camera_id)


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: int, payload: CameraUpdate, session: SessionDep, background: BackgroundTasks
) -> Camera:
    camera = await _get_camera(session, camera_id)
    changes = payload.model_dump(exclude_unset=True)
    current = CameraBase.model_validate(camera, from_attributes=True).model_dump()
    try:
        CameraBase.model_validate(current | changes)
    except ValidationError as exc:
        raise HTTPException(422, json.loads(exc.json(include_url=False))) from exc
    for key, value in changes.items():
        setattr(camera, key, value)
    await _commit(session)
    if changes.keys() & {"match_type", "match_value", "priority", "enabled"}:
        background.add_task(scanner.rematch)
    return camera


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(camera_id: int, session: SessionDep, background: BackgroundTasks) -> None:
    camera = await _get_camera(session, camera_id)
    await session.delete(camera)
    await session.commit()
    background.add_task(scanner.rematch)
