import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.models import Camera, MatchType

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MatchRule:
    camera_id: int
    match_type: MatchType
    value: str
    pattern: re.Pattern[str] | None
    timestamp_pattern: re.Pattern[str] | None


class CameraMatcher:
    """Assigns a relative recording path to the first matching camera, ordered by priority."""

    def __init__(self, cameras: Iterable[Camera]) -> None:
        ordered = sorted((c for c in cameras if c.enabled), key=lambda c: (c.priority, c.id))
        self.rules = [rule for rule in map(self._compile, ordered) if rule is not None]

    @staticmethod
    def _compile(camera: Camera) -> MatchRule | None:
        try:
            pattern = re.compile(camera.match_value, re.IGNORECASE) if camera.match_type == MatchType.regex else None
            timestamp_pattern = re.compile(camera.timestamp_regex) if camera.timestamp_regex else None
        except re.error as exc:
            log.warning("Camera %r has an invalid regex and is ignored: %s", camera.name, exc)
            return None
        value = camera.match_value.strip().replace("\\", "/").strip("/").lower()
        return MatchRule(camera.id, camera.match_type, value, pattern, timestamp_pattern)

    def match(self, rel_path: str) -> MatchRule | None:
        posix = rel_path.replace("\\", "/")
        lowered = posix.lower()
        folders, _, filename = lowered.rpartition("/")
        folder_parts = folders.split("/") if folders else []

        for rule in self.rules:
            if rule.match_type == MatchType.folder:
                hit = lowered.startswith(rule.value + "/") if "/" in rule.value else rule.value in folder_parts
            elif rule.match_type == MatchType.prefix:
                hit = filename.startswith(rule.value)
            else:
                hit = rule.pattern is not None and rule.pattern.search(posix) is not None
            if hit:
                return rule
        return None
