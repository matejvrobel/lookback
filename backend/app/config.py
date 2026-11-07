from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(BaseSettings):
    """Bootstrap settings from LOOKBACK_* environment variables. Everything else lives in the database."""

    model_config = SettingsConfigDict(env_prefix="LOOKBACK_")

    config_dir: Path = Path("/config")
    media_dir: Path = Path("/recordings")
    cache_dir: Path = Path("/cache")
    static_dir: Path = Path("/app/static")
    log_level: str = "INFO"

    @property
    def db_path(self) -> Path:
        return self.config_dir / "lookback.db"

    @property
    def thumbs_dir(self) -> Path:
        return self.cache_dir / "thumbs"

    @property
    def remux_dir(self) -> Path:
        return self.cache_dir / "remux"

    @property
    def hls_dir(self) -> Path:
        return self.cache_dir / "hls"

    def ensure_dirs(self) -> None:
        for path in (self.config_dir, self.thumbs_dir, self.remux_dir, self.hls_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_env() -> Environment:
    return Environment()
