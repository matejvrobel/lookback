import datetime as dt

from pydantic import BaseModel


class TimelineClip(BaseModel):
    id: int
    start: float
    end: float
    thumb_ready: bool = False
    thumb_count: int = 0
    thumb_interval: float | None = None


class TimelineSpan(BaseModel):
    start: float
    end: float
    clip_count: int = 1


class TimelineLane(BaseModel):
    camera_id: int | None
    name: str
    color: str
    spans: list[TimelineSpan] = []
    clips: list[TimelineClip] = []


class TimelineResponse(BaseModel):
    date: dt.date
    timezone: str
    day_start: float
    day_end: float
    lanes: list[TimelineLane]


class CalendarDay(BaseModel):
    date: dt.date
    clips: int
    duration: float
    camera_ids: list[int | None]


class CalendarBounds(BaseModel):
    first_day: dt.date | None
    last_day: dt.date | None
