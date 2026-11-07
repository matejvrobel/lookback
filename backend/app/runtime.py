from app.config import get_env
from app.services.playback import HlsManager, RemuxCache
from app.services.scanner import Scanner
from app.services.tasks import TaskManager
from app.services.thumbnails import ThumbnailWorker

_env = get_env()

scanner = Scanner()
thumbnail_worker = ThumbnailWorker(_env.thumbs_dir)
remux_cache = RemuxCache(_env.remux_dir)
hls_manager = HlsManager(_env.hls_dir)
task_manager = TaskManager(scanner, thumbnail_worker, remux_cache, hls_manager)
