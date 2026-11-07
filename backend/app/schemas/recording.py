import enum

from pydantic import BaseModel, ConfigDict

from app.models import ThumbStatus


class PlaybackMethod(str, enum.Enum):
    direct = "direct"
    remux = "remux"
    hls = "hls"


class RecordingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int | None
    rel_path: str
    size: int
    start_ts: float
    end_ts: float
    duration: float
    day: str
    timestamp_source: str
    container: str
    video_codec: str | None
    audio_codec: str | None
    width: int | None
    height: int | None
    fps: float | None
    probe_error: str | None
    thumb_status: ThumbStatus
    thumb_count: int
    thumb_interval: float | None


class RecordingPage(BaseModel):
    total: int
    items: list[RecordingOut]


class AdjacentRecordings(BaseModel):
    previous: RecordingOut | None
    next: RecordingOut | None
    gap_before: float | None
    gap_after: float | None


class PlaybackInfo(BaseModel):
    recording_id: int
    method: PlaybackMethod
    url: str
    mime_type: str
