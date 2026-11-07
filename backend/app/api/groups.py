from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.models import Camera, CameraGroup
from app.schemas.camera import GroupCreate, GroupOut, GroupUpdate

router = APIRouter(prefix="/groups", tags=["groups"])


def _to_out(group: CameraGroup) -> GroupOut:
    return GroupOut(
        id=group.id,
        name=group.name,
        sort_order=group.sort_order,
        camera_ids=[camera.id for camera in group.cameras],
    )


async def _load_cameras(session: SessionDep, camera_ids: list[int]) -> list[Camera]:
    cameras = (await session.scalars(select(Camera).where(Camera.id.in_(camera_ids)))).all()
    missing = set(camera_ids) - {camera.id for camera in cameras}
    if missing:
        raise HTTPException(422, f"Unknown camera ids: {sorted(missing)}")
    return list(cameras)


async def _get_group(session: SessionDep, group_id: int) -> CameraGroup:
    group = await session.get(CameraGroup, group_id)
    if group is None:
        raise HTTPException(404, "Camera group not found")
    return group


async def _commit(session: SessionDep) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "A group with this name already exists") from exc


@router.get("", response_model=list[GroupOut])
async def list_groups(session: SessionDep) -> list[GroupOut]:
    groups = (await session.scalars(select(CameraGroup).order_by(CameraGroup.sort_order, CameraGroup.name))).all()
    return [_to_out(group) for group in groups]


@router.post("", response_model=GroupOut, status_code=201)
async def create_group(payload: GroupCreate, session: SessionDep) -> GroupOut:
    group = CameraGroup(name=payload.name, sort_order=payload.sort_order)
    group.cameras = await _load_cameras(session, payload.camera_ids)
    session.add(group)
    await _commit(session)
    return _to_out(group)


@router.patch("/{group_id}", response_model=GroupOut)
async def update_group(group_id: int, payload: GroupUpdate, session: SessionDep) -> GroupOut:
    group = await _get_group(session, group_id)
    changes = payload.model_dump(exclude_unset=True)
    if "camera_ids" in changes:
        group.cameras = await _load_cameras(session, changes.pop("camera_ids") or [])
    for key, value in changes.items():
        setattr(group, key, value)
    await _commit(session)
    return _to_out(group)


@router.delete("/{group_id}", status_code=204)
async def delete_group(group_id: int, session: SessionDep) -> None:
    await session.delete(await _get_group(session, group_id))
    await session.commit()
