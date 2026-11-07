import asyncio
import logging
import os
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.models import Recording
from app.schemas.recording import PlaybackMethod
from app.schemas.settings import AppSettings, FFmpegSettings, PlaybackSettings
from app.services import ffmpeg

log = logging.getLogger(__name__)

PLAYLIST_WAIT_SECONDS = 20


class PlaybackError(RuntimeError):
    pass


def choose_method(recording: Recording, config: PlaybackSettings) -> PlaybackMethod:
    if config.mode == "transcode" or recording.video_codec not in config.direct_video_codecs:
        return PlaybackMethod.hls
    if recording.container == "mp4" and _audio_ok(recording, config):
        return PlaybackMethod.direct
    return PlaybackMethod.remux


def _audio_ok(recording: Recording, config: PlaybackSettings) -> bool:
    return recording.audio_codec is None or recording.audio_codec in config.direct_audio_codecs


def _is_fresh(path: Path, source_mtime: float) -> bool:
    try:
        return path.stat().st_mtime >= source_mtime
    except FileNotFoundError:
        return False


class RemuxCache:
    """Stream-copies browser-compatible MKVs into faststart MP4s so they can be served with Range support."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    def path_for(self, recording_id: int) -> Path:
        return self.directory / f"{recording_id}.mp4"

    async def ensure(self, recording: Recording, settings: AppSettings) -> Path:
        target = self.path_for(recording.id)
        async with self._locks[recording.id]:
            if _is_fresh(target, recording.mtime):
                os.utime(target)
                return target

            ff = settings.ffmpeg
            temp = target.with_name(f"{recording.id}.mp4.part")
            audio_args = (
                ["-c:a", "copy"]
                if _audio_ok(recording, settings.playback)
                else ["-c:a", "aac", "-b:a", ff.audio_bitrate, "-ac", "2"]
            )
            video_tag = ["-tag:v", "hvc1"] if recording.video_codec == "hevc" else []
            args = [
                ff.ffmpeg_path, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                *ff.extra_input_args, "-i", recording.path,
                "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "copy", *video_tag, *audio_args,
                "-movflags", "+faststart", "-f", "mp4", str(temp),
            ]
            code, _, stderr = await ffmpeg.run(args, timeout=900)
            if code != 0:
                temp.unlink(missing_ok=True)
                raise PlaybackError(f"Remux failed: {stderr.decode(errors='replace')[:300]}")
            os.replace(temp, target)
            return target


def _video_args(ff: FFmpegSettings) -> tuple[list[str], list[str]]:
    quality = str(ff.video_quality)
    if ff.hwaccel == "vaapi":
        return (
            ["-hwaccel", "vaapi", "-hwaccel_device", ff.hwaccel_device, "-hwaccel_output_format", "vaapi"],
            ["-vf", "scale_vaapi=format=nv12", "-c:v", "h264_vaapi", "-qp", quality],
        )
    if ff.hwaccel == "qsv":
        return (
            ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"],
            ["-c:v", "h264_qsv", "-preset", ff.video_preset, "-global_quality", quality],
        )
    if ff.hwaccel == "nvenc":
        return (
            ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"],
            ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", quality],
        )
    return (
        [],
        ["-c:v", "libx264", "-preset", ff.video_preset, "-crf", quality, "-pix_fmt", "yuv420p", "-profile:v", "high"],
    )


def build_hls_args(recording: Recording, ff: FFmpegSettings, directory: Path) -> list[str]:
    segment = ff.hls_segment_seconds
    input_args, video_args = _video_args(ff)
    return [
        ff.ffmpeg_path, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        *input_args, *ff.extra_input_args, "-i", recording.path,
        "-map", "0:v:0", "-map", "0:a:0?",
        *video_args,
        "-force_key_frames", f"expr:gte(t,n_forced*{segment})",
        "-c:a", "aac", "-b:a", ff.audio_bitrate, "-ac", "2",
        *ff.extra_output_args,
        "-f", "hls",
        "-hls_time", str(segment),
        "-hls_playlist_type", "event",
        "-hls_flags", "temp_file+independent_segments",
        "-hls_segment_filename", str(directory / "seg_%05d.ts"),
        str(directory / "index.m3u8"),
    ]


@dataclass
class HlsJob:
    directory: Path
    process: asyncio.subprocess.Process | None
    last_access: float

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.returncode is None


class HlsManager:
    """Runs one ffmpeg HLS job per recording; finished playlists stay in the cache until pruned."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._jobs: dict[int, HlsJob] = {}
        self._lock = asyncio.Lock()
        self._watchers: set[asyncio.Task] = set()

    def job_dir(self, recording_id: int) -> Path:
        return self.directory / str(recording_id)

    def touch(self, recording_id: int) -> None:
        job = self._jobs.get(recording_id)
        if job:
            job.last_access = time.monotonic()

    def active_dirs(self) -> set[Path]:
        return {job.directory for job in self._jobs.values() if job.running}

    async def ensure(self, recording: Recording, settings: AppSettings) -> Path:
        directory = self.job_dir(recording.id)
        playlist = directory / "index.m3u8"
        async with self._lock:
            job = self._jobs.get(recording.id)
            if job is None or not (job.running or _is_reusable(playlist, recording.mtime)):
                job = await self._start(recording, settings.ffmpeg, directory)
                self._jobs[recording.id] = job
            job.last_access = time.monotonic()
            os.utime(directory)

        deadline = time.monotonic() + PLAYLIST_WAIT_SECONDS
        while time.monotonic() < deadline:
            if _has_segment(playlist):
                return playlist
            if not job.running:
                break
            await asyncio.sleep(0.25)
        if _has_segment(playlist):
            return playlist
        raise PlaybackError("HLS transcode did not produce a playlist in time")

    async def _start(self, recording: Recording, ff: FFmpegSettings, directory: Path) -> HlsJob:
        if _is_reusable(directory / "index.m3u8", recording.mtime):
            return HlsJob(directory, None, time.monotonic())
        shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True, exist_ok=True)
        process = await asyncio.create_subprocess_exec(
            *build_hls_args(recording, ff, directory),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        watcher = asyncio.create_task(self._log_exit(recording.id, process))
        self._watchers.add(watcher)
        watcher.add_done_callback(self._watchers.discard)
        log.info("Started HLS transcode for recording %d", recording.id)
        return HlsJob(directory, process, time.monotonic())

    @staticmethod
    async def _log_exit(recording_id: int, process: asyncio.subprocess.Process) -> None:
        _, stderr = await process.communicate()
        if process.returncode not in (0, -9, 137):
            log.warning(
                "HLS transcode for recording %d exited with %s: %s",
                recording_id,
                process.returncode,
                stderr.decode(errors="replace")[:300],
            )

    async def reap_idle(self, timeout: float) -> None:
        now = time.monotonic()
        async with self._lock:
            for recording_id, job in list(self._jobs.items()):
                if now - job.last_access < timeout:
                    continue
                if job.running:
                    job.process.kill()
                    shutil.rmtree(job.directory, ignore_errors=True)
                del self._jobs[recording_id]

    async def shutdown(self) -> None:
        for job in self._jobs.values():
            if job.running:
                job.process.kill()
        self._jobs.clear()


def _is_complete(playlist: Path) -> bool:
    try:
        return "#EXT-X-ENDLIST" in playlist.read_text()
    except OSError:
        return False


def _is_reusable(playlist: Path, source_mtime: float) -> bool:
    return _is_complete(playlist) and _is_fresh(playlist, source_mtime)


def _has_segment(playlist: Path) -> bool:
    try:
        return ".ts" in playlist.read_text()
    except OSError:
        return False


def _entry_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def prune_cache(directories: list[Path], limit_bytes: int, protected: set[Path]) -> int:
    entries = []
    for directory in directories:
        if not directory.exists():
            continue
        for child in directory.iterdir():
            if child in protected or child.name.endswith(".part"):
                continue
            try:
                entries.append((child.stat().st_mtime, _entry_size(child), child))
            except OSError:
                continue

    total = sum(size for _, size, _ in entries)
    removed = 0
    for _, size, path in sorted(entries):
        if total <= limit_bytes:
            break
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        total -= size
        removed += 1
    return removed
