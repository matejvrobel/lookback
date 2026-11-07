import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

MIN_VALID_EPOCH = 946684800.0
PROGRESS_TIME = re.compile(rb"time=(\d+):(\d{2}):(\d{2}(?:\.\d+)?)")


@dataclass(slots=True)
class ProbeResult:
    duration: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    creation_time: float | None = None
    error: str | None = None


async def run(args: list[str], timeout: float | None = None) -> tuple[int, bytes, bytes]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return -1, b"", b"timed out"
    return process.returncode or 0, stdout, stderr


async def version(ffmpeg_path: str) -> str | None:
    try:
        code, stdout, _ = await run([ffmpeg_path, "-hide_banner", "-version"], timeout=10)
    except OSError:
        return None
    return stdout.decode(errors="replace").splitlines()[0] if code == 0 and stdout else None


async def probe(path: str, ffprobe_path: str) -> ProbeResult:
    args = [ffprobe_path, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    try:
        code, stdout, stderr = await run(args, timeout=60)
    except OSError as exc:
        return ProbeResult(error=f"Cannot run ffprobe: {exc}")
    if code != 0:
        message = stderr.decode(errors="replace").strip()
        return ProbeResult(error=(message or f"ffprobe exited with code {code}")[:500])

    try:
        info = json.loads(stdout or b"{}")
    except json.JSONDecodeError as exc:
        return ProbeResult(error=f"Invalid ffprobe output: {exc}")

    fmt = info.get("format", {})
    result = ProbeResult(duration=_to_float(fmt.get("duration")))
    for stream in info.get("streams", []):
        kind = stream.get("codec_type")
        if kind == "video" and result.video_codec is None and not stream.get("disposition", {}).get("attached_pic"):
            result.video_codec = stream.get("codec_name")
            result.width = stream.get("width")
            result.height = stream.get("height")
            result.fps = _parse_rate(stream.get("avg_frame_rate") or stream.get("r_frame_rate"))
            if result.duration is None:
                result.duration = _to_float(stream.get("duration"))
        elif kind == "audio" and result.audio_codec is None:
            result.audio_codec = stream.get("codec_name")

    created = fmt.get("tags", {}).get("creation_time")
    if created:
        try:
            timestamp = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
            if timestamp > MIN_VALID_EPOCH:
                result.creation_time = timestamp
        except ValueError:
            pass
    return result


async def measure_duration(path: str, ffmpeg_path: str) -> float | None:
    """Fallback for containers without a duration header (e.g. live-muxed MKV): stream-copy to null and read the clock."""
    args = [ffmpeg_path, "-hide_banner", "-nostdin", "-stats", "-i", path, "-map", "0:v:0", "-c", "copy", "-f", "null", "-"]
    try:
        code, _, stderr = await run(args, timeout=300)
    except OSError:
        return None
    matches = PROGRESS_TIME.findall(stderr)
    if code != 0 or not matches:
        return None
    hours, minutes, seconds = matches[-1]
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


async def get_duration(path: str, ffprobe_path: str, ffmpeg_path: str) -> float | None:
    result = await probe(path, ffprobe_path)
    if result.duration:
        return result.duration
    return await measure_duration(path, ffmpeg_path)


async def _render_image(args: list[str], target: Path, timeout: float) -> str | None:
    temp = target.with_name(f"{target.stem}.tmp{target.suffix}")
    try:
        code, _, stderr = await run([*args, str(temp)], timeout=timeout)
    except OSError as exc:
        return f"Cannot run ffmpeg: {exc}"
    if code != 0 or not temp.exists():
        temp.unlink(missing_ok=True)
        return stderr.decode(errors="replace").strip()[:300] or f"ffmpeg exited with code {code}"
    os.replace(temp, target)
    return None


async def generate_thumbnail(
    ffmpeg_path: str, source: str, target: Path, at_seconds: float, width: int, quality: int
) -> str | None:
    """Writes a single JPEG frame; returns an error message or None on success."""
    return await _render_image(
        [
            ffmpeg_path, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-ss", f"{at_seconds:.3f}", "-i", source,
            "-an", "-sn", "-frames:v", "1",
            "-vf", f"scale={width}:-2", "-q:v", str(quality), "-update", "1",
        ],
        target,
        timeout=60,
    )


async def generate_sprite(
    ffmpeg_path: str, source: str, target: Path, interval: float, count: int, width: int, quality: int
) -> str | None:
    """Writes a 1-row sprite of `count` frames, one every `interval` seconds, decoding keyframes only."""
    return await _render_image(
        [
            ffmpeg_path, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-skip_frame", "nokey", "-i", source,
            "-an", "-sn", "-frames:v", "1",
            "-vf", f"fps=1/{interval:.3f},scale={width}:-2,tile={count}x1",
            "-q:v", str(quality), "-update", "1",
        ],
        target,
        timeout=300,
    )


def _to_float(value) -> float | None:
    try:
        return float(value) if value not in (None, "N/A") else None
    except (TypeError, ValueError):
        return None


def _parse_rate(value: str | None) -> float | None:
    if not value or "/" not in value:
        return _to_float(value)
    numerator, denominator = value.split("/", 1)
    try:
        return round(float(numerator) / float(denominator), 3) if float(denominator) else None
    except ValueError:
        return None
