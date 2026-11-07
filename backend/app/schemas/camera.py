import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import MatchType

HEX_COLOR = r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$"


def _check_regex(value: str | None, label: str) -> None:
    if not value:
        return
    try:
        re.compile(value)
    except re.error as exc:
        raise ValueError(f"Invalid {label}: {exc}") from exc


class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    match_type: MatchType
    match_value: str = Field(min_length=1, max_length=500)
    timestamp_regex: str | None = None
    color: str = Field("#3b82f6", pattern=HEX_COLOR)
    priority: int = 100
    sort_order: int = 0
    enabled: bool = True

    @model_validator(mode="after")
    def _check_regexes(self) -> "CameraBase":
        if self.match_type == MatchType.regex:
            _check_regex(self.match_value, "match regex")
        _check_regex(self.timestamp_regex, "timestamp regex")
        return self


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    match_type: MatchType | None = None
    match_value: str | None = Field(None, min_length=1, max_length=500)
    timestamp_regex: str | None = None
    color: str | None = Field(None, pattern=HEX_COLOR)
    priority: int | None = None
    sort_order: int | None = None
    enabled: bool | None = None


class CameraOut(CameraBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recording_count: int = 0


class MatchTestRequest(BaseModel):
    match_type: MatchType
    match_value: str = Field(min_length=1)


class MatchTestResult(BaseModel):
    matched: int
    samples: list[str]


class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = 0
    camera_ids: list[int] = []


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    sort_order: int | None = None
    camera_ids: list[int] | None = None


class GroupOut(GroupBase):
    id: int
