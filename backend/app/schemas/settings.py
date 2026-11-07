import os
import re
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator

from app.config import get_env

DEFAULT_TIMESTAMP_PATTERNS = [
    r"(?P<Y>20\d{2})[-_.]?(?P<m>[01]\d)[-_.]?(?P<d>[0-3]\d)[T_\-. ]?(?P<H>[0-2]\d)[-_.:]?(?P<M>[0-5]\d)[-_.:]?(?P<S>[0-5]\d)",
    r"(?P<Y>20\d{2})[-_/]?(?P<m>[01]\d)[-_/]?(?P<d>[0-3]\d)/(?:[^/]+/)*[^/]*?(?P<H>[0-2]\d)[-_.:]?(?P<M>[0-5]\d)[-_.:]?(?P<S>[0-5]\d)[^/]*$",
    r"(?<!\d)(?P<epoch>1[5-9]\d{8})(?!\d)",
]


class GeneralSettings(BaseModel):
    instance_name: str = "Lookback"
    timezone: str = Field(default_factory=lambda: os.environ.get("TZ") or "UTC")

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except Exception as exc:
            raise ValueError(f"Unknown timezone: {value}") from exc
        return value


class LibrarySettings(BaseModel):
    root_folders: list[str] = Field(default_factory=lambda: [str(get_env().media_dir)])
    extensions: list[str] = [".mp4", ".mkv"]
    ignore_patterns: list[str] = ["*.part", "*.tmp"]
    min_file_age_seconds: int = Field(30, ge=0)
    remove_missing: bool = True
    timestamp_patterns: list[str] = Field(default_factory=lambda: list(DEFAULT_TIMESTAMP_PATTERNS))

    @field_validator("timestamp_patterns")
    @classmethod
    def _valid_patterns(cls, value: list[str]) -> list[str]:
        for pattern in value:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"Invalid regex {pattern!r}: {exc}") from exc
        return value


class ScannerSettings(BaseModel):
    interval_minutes: int = Field(5, ge=0)
    scan_on_startup: bool = True
    watch_enabled: bool = False
    watch_force_polling: bool = False
    probe_concurrency: int = Field(4, ge=1, le=32)


class PlaybackSettings(BaseModel):
    mode: Literal["auto", "transcode"] = "auto"
    direct_video_codecs: list[str] = ["h264", "vp9", "av1"]
    direct_audio_codecs: list[str] = ["aac", "mp3", "opus"]
    cache_size_mb: int = Field(4096, ge=64)
    hls_idle_timeout_seconds: int = Field(300, ge=30)


class FFmpegSettings(BaseModel):
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    hwaccel: Literal["none", "vaapi", "qsv", "nvenc"] = "none"
    hwaccel_device: str = "/dev/dri/renderD128"
    video_preset: str = "veryfast"
    video_quality: int = Field(23, ge=0, le=51)
    audio_bitrate: str = "128k"
    hls_segment_seconds: int = Field(4, ge=1, le=30)
    extra_input_args: list[str] = []
    extra_output_args: list[str] = []


class ThumbnailSettings(BaseModel):
    enabled: bool = True
    interval_seconds: int = Field(10, ge=1)
    max_per_clip: int = Field(60, ge=1, le=300)
    sprite_width: int = Field(160, ge=64, le=640)
    poster_width: int = Field(320, ge=64, le=1280)
    quality: int = Field(5, ge=2, le=31)
    concurrency: int = Field(1, ge=1, le=8)


class UISettings(BaseModel):
    theme: Literal["dark", "light", "system"] = "dark"
    first_day_of_week: Literal[0, 1] = 1
    time_format: Literal["24h", "12h"] = "24h"
    default_playback_rate: Literal[1, 2, 4, 8] = 1
    autoplay_next: bool = True
    timeline_gap_merge_seconds: int = Field(5, ge=0)
    timeline_show_thumbnails: bool = True


class AppSettings(BaseModel):
    general: GeneralSettings = Field(default_factory=GeneralSettings)
    library: LibrarySettings = Field(default_factory=LibrarySettings)
    scanner: ScannerSettings = Field(default_factory=ScannerSettings)
    playback: PlaybackSettings = Field(default_factory=PlaybackSettings)
    ffmpeg: FFmpegSettings = Field(default_factory=FFmpegSettings)
    thumbnails: ThumbnailSettings = Field(default_factory=ThumbnailSettings)
    ui: UISettings = Field(default_factory=UISettings)


SECTION_MODELS: dict[str, type[BaseModel]] = {
    name: field.annotation for name, field in AppSettings.model_fields.items()
}
