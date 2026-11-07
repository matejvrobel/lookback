from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import CameraIdsQuery, GroupIdQuery, SessionDep, resolve_camera_filter
from app.schemas.timeline import CalendarBounds, CalendarDay, TimelineResponse
from app.services.settings_store import settings_store
from app.services.timeline import available_days, build_calendar, build_timeline, calendar_bounds

router = APIRouter(tags=["timeline"])


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    session: SessionDep,
    day: date = Query(alias="date"),
    camera_ids: CameraIdsQuery = None,
    group_id: GroupIdQuery = None,
) -> TimelineResponse:
    ids = await resolve_camera_filter(session, camera_ids, group_id)
    return await build_timeline(session, day, ids, settings_store.current)


@router.get("/calendar", response_model=list[CalendarDay])
async def get_calendar(
    session: SessionDep,
    year: int = Query(ge=1970, le=2100),
    month: int = Query(ge=1, le=12),
    camera_ids: CameraIdsQuery = None,
    group_id: GroupIdQuery = None,
) -> list[CalendarDay]:
    ids = await resolve_camera_filter(session, camera_ids, group_id)
    return await build_calendar(session, year, month, ids)


@router.get("/calendar/days", response_model=list[date])
async def get_available_days(
    session: SessionDep,
    start: date | None = None,
    end: date | None = None,
    camera_ids: CameraIdsQuery = None,
    group_id: GroupIdQuery = None,
) -> list[date]:
    ids = await resolve_camera_filter(session, camera_ids, group_id)
    return await available_days(session, start, end, ids)


@router.get("/calendar/bounds", response_model=CalendarBounds)
async def get_calendar_bounds(
    session: SessionDep, camera_ids: CameraIdsQuery = None, group_id: GroupIdQuery = None
) -> CalendarBounds:
    ids = await resolve_camera_filter(session, camera_ids, group_id)
    return await calendar_bounds(session, ids)
