import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import api_router
from app.config import get_env
from app.database import SessionLocal, init_db
from app.frontend import mount_frontend
from app.runtime import task_manager
from app.services.settings_store import settings_store

log = logging.getLogger("recordviewer")


@asynccontextmanager
async def lifespan(_: FastAPI):
    env = get_env()
    logging.basicConfig(
        level=env.log_level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    env.ensure_dirs()
    await init_db()
    async with SessionLocal() as session:
        await settings_store.load(session)
    await task_manager.start()
    log.info("RecordViewer %s started", __version__)
    try:
        yield
    finally:
        await task_manager.stop()


app = FastAPI(
    title="RecordViewer",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.include_router(api_router)
mount_frontend(app, get_env().static_dir)
