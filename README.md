# Lookback

Self-hosted archive viewer for NVR and security camera recordings.

Lookback indexes the MP4/MKV files your cameras or NVR already write to disk and lets you browse them on a calendar and a per-day timeline, with hover thumbnails, fast playback and seamless auto-play across chunks. It is deliberately **not** an NVR: no live view, no motion detection, no recording. It only plays back what is already there.

The UI follows the style of the *arr apps (Sonarr, Radarr): dark by default, sidebar navigation, and a settings page with sections.

## Features

- **Calendar and timeline.** Pick a day, see every camera as its own lane, zoom down to individual clips and hover to preview the exact frame.
- **Cameras and groups.** A camera is a rule: a folder, a filename prefix or a regex. Show one camera, a group or all of them on the same time axis.
- **Player.** 1×/2×/4×/8× speed, previous/next clip, download, and **auto-play next**: the next chunk is preloaded into a second video element and swapped in when the current one ends, so 1–2 minute chunks play as one continuous stream.
- **Works with what you have.** Browser-compatible MP4 is served directly with HTTP Range (seekable). H.264 MKV is remuxed to MP4 on the fly. Anything else is transcoded to HLS with FFmpeg, optionally with VAAPI, Quick Sync or NVENC.
- **Timestamps from filenames.** Built-in patterns cover common NVR naming (`20260826-103639.mp4`, `ch01_20240115143000.mkv`, `2024-01-15/001/dav/14/14.30.00-…`, Unix timestamps). You can add your own regexes.
- **Scanner.** Periodic scans plus an optional file watcher. Unchanged files are skipped, files still being written are left for the next scan, and an offline share never wipes the index.
- **No login.** Run it on your LAN or behind a reverse proxy that handles authentication (see [Security](#security)).

## Installation

Lookback is published as a multi-arch image (`linux/amd64`, `linux/arm64`):

```
ghcr.io/matejvrobel/lookback:latest
```

You need a host with Docker. Mount your recordings read-only at `/recordings`.

### Dockge

1. In Dockge click **+ Compose** and name the stack `lookback`.
2. Paste one of the compose files below into the editor:
   - Recordings in a folder on the host: [`compose.yaml`](compose.yaml)
   - Recordings on an SMB/NAS share: [`examples/compose.smb.yaml`](examples/compose.smb.yaml)
3. Fill in the **.env** editor below the compose file. For the SMB variant, use [`examples/smb.env`](examples/smb.env) as a template:

   ```ini
   PUID=1000
   PGID=1000
   TZ=Europe/Prague
   PORT=8765
   SMB_HOST=192.168.1.10
   SMB_SHARE=Media/Camera
   SMB_USER=camera
   SMB_PASS=change-me
   ```

   For the host-folder variant, set `RECORDINGS_PATH` instead of the `SMB_*` variables.
4. Click **Deploy**, then open `http://<server>:8765`.

To update later, open the stack and click **Update**. Dockge pulls the new `latest` image and recreates the container.

### Docker Compose (CLI)

```bash
mkdir lookback
```

```bash
cd lookback
```

```bash
curl -fsSLo compose.yaml https://raw.githubusercontent.com/matejvrobel/lookback/main/compose.yaml
```

Create a `.env` file next to it (see the variables below), then start it:

```bash
docker compose up -d
```

Update:

```bash
docker compose pull
```

```bash
docker compose up -d
```

### Recordings on an SMB / NAS share

[`examples/compose.smb.yaml`](examples/compose.smb.yaml) mounts the share with Docker's built-in CIFS volume driver, so nothing has to be mounted on the host first.

- `SMB_SHARE` is the share name plus an optional sub-folder, written with forward slashes. For `\\192.168.1.10\Media\Camera` use `SMB_HOST=192.168.1.10` and `SMB_SHARE=Media/Camera`.
- The share is mounted read-only. Lookback never writes to your recordings.
- If the password contains a comma, mount the share on the host instead (for example via `/etc/fstab`) and use `compose.yaml` with `RECORDINGS_PATH` pointing at the mount.
- If the mount fails with an error mentioning the protocol, set `SMB_VERSION=2.1` or `SMB_VERSION=2.0` for older NAS firmware.
- Docker creates the volume on the first deploy. After changing any `SMB_*` value, remove the old volume (`docker volume rm lookback_recordings`) and deploy again, otherwise the old options stay in effect.

### First steps in the UI

1. **Settings → General:** check the timezone. Times in filenames are read in this zone, and days on the calendar are split by it. It defaults to `TZ` from the environment.
2. **Settings → Library:** the recording folder defaults to `/recordings`. Add more folders if you mount several.
3. **Settings → Cameras → Add Camera:**
   - One folder per camera (`/recordings/FrontDoor/...`): match by **Folder** with the folder name.
   - Files of all cameras in one folder with a prefix (`front_...`): match by **Filename prefix**.
   - Anything else, or a single camera whose files sit directly in the root: match by **Regex**, for example `^\d{8}-\d{6}`.

   Use **Test** to see which indexed files a rule would claim.
4. **Settings → Scanner → Scan Now.** Thumbnails are generated in the background afterwards.

## Configuration

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `PUID` / `PGID` | `1000` | User and group the app runs as. `/config` and `/cache` are handed over to them on start. |
| `TZ` | `UTC` | Default timezone for filename timestamps and calendar days. |
| `PORT` | `8765` | Host port (compose files only). |
| `RECORDINGS_PATH` | `./recordings` | Host folder with recordings (`compose.yaml`). |
| `SMB_HOST`, `SMB_SHARE`, `SMB_USER`, `SMB_PASS`, `SMB_VERSION` | | SMB share settings (`examples/compose.smb.yaml`). |

Everything else (paths, scan interval, cameras, groups, FFmpeg, thumbnails, UI) is configured in the web UI and stored in the database.

### Volumes

| Path | Description |
|---|---|
| `/config` | SQLite database (`lookback.db`) with the index and all settings. Back this up. |
| `/cache` | Thumbnails, remuxed MP4s and HLS segments. Safe to delete; the size limit is set in **Settings → Playback**. |
| `/recordings` | Your recordings, mounted read-only. |

### Timestamps

The start time of a clip is taken from, in order:

1. the filename or path, using the patterns in **Settings → Library** (plus an optional per-camera regex),
2. the `creation_time` metadata in the file,
3. the file's modification time minus its duration.

Patterns are regular expressions with named groups `Y`, `m`, `d`, `H`, `M`, `S`, or a single `epoch` group, for example:

```
(?P<Y>\d{4})(?P<m>\d{2})(?P<d>\d{2})-(?P<H>\d{2})(?P<M>\d{2})(?P<S>\d{2})
```

Changing the timezone or the patterns re-indexes the library.

### Hardware acceleration

Only recordings whose video codec the browser cannot play are transcoded. H.264 video in MP4 or MKV is never re-encoded.

1. Uncomment `devices: - /dev/dri:/dev/dri` in the compose file. The container picks up the render group of the device automatically.
2. In **Settings → Playback → Hardware acceleration** choose VAAPI or Quick Sync.

The image ships Debian's FFmpeg. NVENC additionally requires the NVIDIA Container Toolkit and a GPU reservation in the compose file.

## Security

Lookback has **no authentication**. Do not expose it to the internet directly. Keep it on your LAN or put it behind a reverse proxy with authentication (Authelia, Authentik, or basic auth in Nginx, Caddy or Traefik).

## Development

Backend (Python 3.11+, FFmpeg on `PATH`):

```bash
cd backend
```

```bash
python -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```bash
LOOKBACK_CONFIG_DIR=../dev/config LOOKBACK_CACHE_DIR=../dev/cache LOOKBACK_MEDIA_DIR=../recordings uvicorn app.main:app --reload --port 8765
```

The API docs are at `http://localhost:8765/api/docs`.

Frontend (Node 22), in a second terminal. Vite proxies `/api` to the backend on port 8765:

```bash
cd frontend
```

```bash
npm ci
```

```bash
npm run dev
```

Build the image locally:

```bash
docker build -t lookback:dev .
```

### Project layout

```
backend/app/
  api/          FastAPI routers (settings, cameras, groups, timeline, recordings, playback)
  models/       SQLAlchemy models (cameras, groups, recordings, settings)
  schemas/      Pydantic schemas, including all settings with their defaults
  services/     scanner, camera matcher, FFmpeg helpers, thumbnails, playback cache, scheduler
frontend/src/
  components/   UI kit, layout, settings dialogs, calendar, timeline, player
  views/        Calendar/playback, Settings sections, System
docker/         container entrypoint
examples/       compose and .env templates
```

### Releases

Every push to `main` publishes `ghcr.io/matejvrobel/lookback:latest` through GitHub Actions ([`.github/workflows/docker.yml`](.github/workflows/docker.yml)). Pushing a tag such as `v1.2.0` also publishes `1.2.0` and `1.2`, so you can pin a version in the compose file instead of `latest`.
