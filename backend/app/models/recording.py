import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow


class ThumbStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    failed = "failed"


class Recording(Base):
    __tablename__ = "recordings"
    __table_args__ = (
        Index("ix_recordings_camera_start", "camera_id", "start_ts"),
        Index("ix_recordings_day_camera", "day", "camera_id"),
        Index("ix_recordings_thumb_status", "thumb_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"))

    path: Mapped[str] = mapped_column(String(1024), unique=True)
    root: Mapped[str] = mapped_column(String(512))
    rel_path: Mapped[str] = mapped_column(String(1024))
    size: Mapped[int] = mapped_column(BigInteger)
    mtime: Mapped[float]

    start_ts: Mapped[float] = mapped_column(index=True)
    end_ts: Mapped[float] = mapped_column(index=True)
    duration: Mapped[float]
    day: Mapped[str] = mapped_column(String(10))
    timestamp_source: Mapped[str] = mapped_column(String(16))

    container: Mapped[str] = mapped_column(String(16))
    video_codec: Mapped[str | None] = mapped_column(String(32))
    audio_codec: Mapped[str | None] = mapped_column(String(32))
    width: Mapped[int | None]
    height: Mapped[int | None]
    fps: Mapped[float | None]
    probe_error: Mapped[str | None] = mapped_column(Text)

    thumb_status: Mapped[ThumbStatus] = mapped_column(
        Enum(ThumbStatus, native_enum=False, length=16), default=ThumbStatus.pending
    )
    thumb_count: Mapped[int] = mapped_column(default=0)
    thumb_interval: Mapped[float | None]

    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
