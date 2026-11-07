import calendar
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Camera, Recording, ThumbStatus
from app.schemas.settings import AppSettings
from app.schemas.timeline import CalendarBounds, CalendarDay, TimelineClip, TimelineLane, TimelineResponse, TimelineSpan
from app.services.timestamps import day_bounds

UNASSIGNED_COLOR = "#6b7280"


async def build_timeline(
    session: AsyncSession, day: date, camera_ids: list[int] | None, settings: AppSettings
) -> TimelineResponse:
    tz = ZoneInfo(settings.general.timezone)
    day_start, day_end = day_bounds(day, tz)
    gap = settings.ui.timeline_gap_merge_seconds

    camera_stmt = select(Camera).order_by(Camera.sort_order, Camera.name)
    recording_stmt = (
        select(
            Recording.id,
            Recording.camera_id,
            Recording.start_ts,
            Recording.end_ts,
            Recording.thumb_status,
            Recording.thumb_count,
            Recording.thumb_interval,
        )
        .where(Recording.start_ts < day_end, Recording.end_ts > day_start)
        .order_by(Recording.start_ts, Recording.id)
    )
    if camera_ids is not None:
        camera_stmt = camera_stmt.where(Camera.id.in_(camera_ids))
        recording_stmt = recording_stmt.where(Recording.camera_id.in_(camera_ids))

    lanes: dict[int | None, TimelineLane] = {
        camera.id: TimelineLane(camera_id=camera.id, name=camera.name, color=camera.color)
        for camera in (await session.scalars(camera_stmt)).all()
    }

    for row in await session.execute(recording_stmt):
        lane = lanes.get(row.camera_id)
        if lane is None:
            lane = lanes.setdefault(
                row.camera_id, TimelineLane(camera_id=None, name="Unassigned", color=UNASSIGNED_COLOR)
            )
        lane.clips.append(
            TimelineClip(
                id=row.id,
                start=row.start_ts,
                end=row.end_ts,
                thumb_ready=row.thumb_status == ThumbStatus.done,
                thumb_count=row.thumb_count,
                thumb_interval=row.thumb_interval,
            )
        )
        last = lane.spans[-1] if lane.spans else None
        if last is not None and row.start_ts - last.end <= gap:
            last.end = max(last.end, row.end_ts)
            last.clip_count += 1
        else:
            lane.spans.append(TimelineSpan(start=row.start_ts, end=row.end_ts))

    return TimelineResponse(
        date=day,
        timezone=tz.key,
        day_start=day_start,
        day_end=day_end,
        lanes=list(lanes.values()),
    )


async def build_calendar(
    session: AsyncSession, year: int, month: int, camera_ids: list[int] | None
) -> list[CalendarDay]:
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    stmt = (
        select(Recording.day, Recording.camera_id, func.count(), func.sum(Recording.duration))
        .where(Recording.day >= first.isoformat(), Recording.day <= last.isoformat())
        .group_by(Recording.day, Recording.camera_id)
        .order_by(Recording.day)
    )
    if camera_ids is not None:
        stmt = stmt.where(Recording.camera_id.in_(camera_ids))

    days: dict[str, CalendarDay] = {}
    for day, camera_id, clips, duration in await session.execute(stmt):
        entry = days.setdefault(day, CalendarDay(date=date.fromisoformat(day), clips=0, duration=0, camera_ids=[]))
        entry.clips += clips
        entry.duration += duration or 0
        entry.camera_ids.append(camera_id)
    return list(days.values())


async def available_days(
    session: AsyncSession, start: date | None, end: date | None, camera_ids: list[int] | None
) -> list[date]:
    stmt = select(Recording.day).distinct().order_by(Recording.day)
    if start is not None:
        stmt = stmt.where(Recording.day >= start.isoformat())
    if end is not None:
        stmt = stmt.where(Recording.day <= end.isoformat())
    if camera_ids is not None:
        stmt = stmt.where(Recording.camera_id.in_(camera_ids))
    return [date.fromisoformat(day) for day in await session.scalars(stmt)]


async def calendar_bounds(session: AsyncSession, camera_ids: list[int] | None) -> CalendarBounds:
    stmt = select(func.min(Recording.day), func.max(Recording.day))
    if camera_ids is not None:
        stmt = stmt.where(Recording.camera_id.in_(camera_ids))
    first, last = (await session.execute(stmt)).one()
    return CalendarBounds(
        first_day=date.fromisoformat(first) if first else None,
        last_day=date.fromisoformat(last) if last else None,
    )
