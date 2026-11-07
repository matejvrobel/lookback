import os
import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from app.api.deps import RecordingDep
from app.api.ranges import ranged_file_response
from app.runtime import hls_manager, remux_cache, task_manager
from app.schemas.recording import PlaybackInfo, PlaybackMethod
from app.services.playback import PlaybackError, choose_method
from app.services.settings_store import settings_store

router = APIRouter(prefix="/recordings", tags=["playback"])

SEGMENT_NAME = re.compile(r"seg_\d{5}\.ts")
MIME_TYPES = {"mp4": "video/mp4", "mkv": "video/x-matroska"}
ROUTES = {
    PlaybackMethod.direct: ("recording_file", "video/mp4"),
    PlaybackMethod.remux: ("recording_remux", "video/mp4"),
    PlaybackMethod.hls: ("recording_hls", "application/vnd.apple.mpegurl"),
}


@router.get("/{recording_id}/playback", response_model=PlaybackInfo)
async def playback_info(recording: RecordingDep, request: Request) -> PlaybackInfo:
    method = choose_method(recording, settings_store.current.playback)
    route_name, mime_type = ROUTES[method]
    return PlaybackInfo(
        recording_id=recording.id,
        method=method,
        url=request.url_for(route_name, recording_id=recording.id).path,
        mime_type=mime_type,
    )


@router.post("/{recording_id}/prepare", status_code=202)
async def prepare_playback(recording: RecordingDep) -> dict:
    settings = settings_store.current
    method = choose_method(recording, settings.playback)
    if method == PlaybackMethod.remux:
        task_manager.spawn(remux_cache.ensure(recording, settings))
    elif method == PlaybackMethod.hls:
        task_manager.spawn(hls_manager.ensure(recording, settings))
    return {"method": method}


@router.api_route("/{recording_id}/file", methods=["GET", "HEAD"], name="recording_file")
async def recording_file(recording: RecordingDep, request: Request, download: bool = False) -> Response:
    if not os.path.isfile(recording.path):
        raise HTTPException(404, "File no longer exists on disk")
    disposition = "attachment" if download else "inline"
    filename = quote(os.path.basename(recording.path))
    return ranged_file_response(
        request,
        recording.path,
        MIME_TYPES.get(recording.container, "application/octet-stream"),
        headers={"Content-Disposition": f"{disposition}; filename*=utf-8''{filename}"},
    )


@router.api_route("/{recording_id}/remux.mp4", methods=["GET", "HEAD"], name="recording_remux")
async def recording_remux(recording: RecordingDep, request: Request) -> Response:
    try:
        path = await remux_cache.ensure(recording, settings_store.current)
    except PlaybackError as exc:
        raise HTTPException(500, str(exc)) from exc
    return ranged_file_response(request, path, "video/mp4")


@router.get("/{recording_id}/hls/index.m3u8", name="recording_hls")
async def recording_hls_playlist(recording: RecordingDep) -> FileResponse:
    try:
        playlist = await hls_manager.ensure(recording, settings_store.current)
    except PlaybackError as exc:
        raise HTTPException(500, str(exc)) from exc
    return FileResponse(playlist, media_type="application/vnd.apple.mpegurl", headers={"Cache-Control": "no-cache"})


@router.get("/{recording_id}/hls/{segment}")
async def recording_hls_segment(recording_id: int, segment: str, request: Request) -> Response:
    if not SEGMENT_NAME.fullmatch(segment):
        raise HTTPException(404)
    path = hls_manager.job_dir(recording_id) / segment
    if not path.is_file():
        raise HTTPException(404)
    hls_manager.touch(recording_id)
    return ranged_file_response(request, path, "video/mp2t", headers={"Cache-Control": "max-age=3600"})
