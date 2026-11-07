from fastapi import APIRouter

from app.api import cameras, groups, playback, recordings, settings, system, timeline

api_router = APIRouter(prefix="/api")
for module in (system, settings, cameras, groups, timeline, recordings, playback):
    api_router.include_router(module.router)
