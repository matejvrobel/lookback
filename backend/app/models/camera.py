import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow


class MatchType(str, enum.Enum):
    folder = "folder"
    prefix = "prefix"
    regex = "regex"


camera_group_members = Table(
    "camera_group_members",
    Base.metadata,
    Column("group_id", ForeignKey("camera_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("camera_id", ForeignKey("cameras.id", ondelete="CASCADE"), primary_key=True),
)


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    match_type: Mapped[MatchType] = mapped_column(Enum(MatchType, native_enum=False, length=16))
    match_value: Mapped[str] = mapped_column(String(500))
    timestamp_regex: Mapped[str | None] = mapped_column(String(500))
    color: Mapped[str] = mapped_column(String(9), default="#3b82f6")
    priority: Mapped[int] = mapped_column(default=100)
    sort_order: Mapped[int] = mapped_column(default=0)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    groups: Mapped[list["CameraGroup"]] = relationship(
        secondary=camera_group_members, back_populates="cameras", lazy="selectin"
    )


class CameraGroup(Base):
    __tablename__ = "camera_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    cameras: Mapped[list[Camera]] = relationship(
        secondary=camera_group_members,
        back_populates="groups",
        order_by=Camera.sort_order,
        lazy="selectin",
    )
