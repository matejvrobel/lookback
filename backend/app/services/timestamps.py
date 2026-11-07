import logging
import re
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)


def compile_patterns(patterns: Iterable[str]) -> list[re.Pattern[str]]:
    compiled = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            log.warning("Skipping invalid timestamp pattern %r: %s", pattern, exc)
    return compiled


def parse_path_timestamp(rel_path: str, patterns: Iterable[re.Pattern[str]], tz: ZoneInfo) -> float | None:
    posix = rel_path.replace("\\", "/")
    filename = posix.rsplit("/", 1)[-1]
    for pattern in patterns:
        for candidate in (filename, posix):
            match = pattern.search(candidate)
            if match:
                timestamp = _groups_to_timestamp(match.groupdict(), tz)
                if timestamp is not None:
                    return timestamp
    return None


def _groups_to_timestamp(groups: dict[str, str | None], tz: ZoneInfo) -> float | None:
    if groups.get("epoch"):
        return float(groups["epoch"])
    try:
        moment = datetime(
            int(groups["Y"]),
            int(groups["m"]),
            int(groups["d"]),
            int(groups.get("H") or 0),
            int(groups.get("M") or 0),
            int(groups.get("S") or 0),
            tzinfo=tz,
        )
    except (KeyError, TypeError, ValueError):
        return None
    return moment.timestamp()


def local_day(timestamp: float, tz: ZoneInfo) -> str:
    return datetime.fromtimestamp(timestamp, tz).date().isoformat()


def day_bounds(day: date, tz: ZoneInfo) -> tuple[float, float]:
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    return start.timestamp(), end.timestamp()
