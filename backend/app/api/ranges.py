import os
import re
from collections.abc import AsyncIterator
from email.utils import formatdate

import anyio
from fastapi import Request
from fastapi.responses import Response, StreamingResponse

CHUNK_SIZE = 512 * 1024
RANGE_HEADER = re.compile(r"bytes=(\d*)-(\d*)")


class RangeNotSatisfiable(Exception):
    pass


def parse_range(header: str, size: int) -> tuple[int, int] | None:
    """Returns an inclusive (start, end) byte range, or None when the header should be ignored."""
    match = RANGE_HEADER.fullmatch(header.strip())
    if match is None:
        return None
    first, last = match.groups()
    if not first and not last:
        return None
    if not first:
        suffix = int(last)
        if suffix == 0:
            raise RangeNotSatisfiable
        return max(0, size - suffix), size - 1
    start = int(first)
    end = min(int(last), size - 1) if last else size - 1
    if start >= size or start > end:
        raise RangeNotSatisfiable
    return start, end


async def _read_file(path: str, start: int, length: int) -> AsyncIterator[bytes]:
    async with await anyio.open_file(path, "rb") as handle:
        await handle.seek(start)
        remaining = length
        while remaining > 0:
            chunk = await handle.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def ranged_file_response(
    request: Request, path: str | os.PathLike, media_type: str, headers: dict[str, str] | None = None
) -> Response:
    """Serves a file with single-range support (206 Partial Content), If-Range and 416 handling."""
    path = os.fspath(path)
    stat = os.stat(path)
    size = stat.st_size
    etag = f'"{stat.st_mtime_ns:x}-{size:x}"'
    base_headers = {
        "Accept-Ranges": "bytes",
        "ETag": etag,
        "Last-Modified": formatdate(stat.st_mtime, usegmt=True),
        **(headers or {}),
    }

    status_code, start, length = 200, 0, size
    range_header = request.headers.get("range")
    if_range = request.headers.get("if-range")
    if range_header and (if_range is None or if_range == etag):
        try:
            byte_range = parse_range(range_header, size)
        except RangeNotSatisfiable:
            return Response(status_code=416, headers={**base_headers, "Content-Range": f"bytes */{size}"})
        if byte_range is not None:
            start, end = byte_range
            status_code, length = 206, end - start + 1
            base_headers["Content-Range"] = f"bytes {start}-{end}/{size}"

    base_headers["Content-Length"] = str(length)
    if request.method == "HEAD":
        return Response(status_code=status_code, media_type=media_type, headers=base_headers)
    return StreamingResponse(
        _read_file(path, start, length), status_code=status_code, media_type=media_type, headers=base_headers
    )
