"""Non-secret configuration loader (AD-20).

Reads config/settings.yaml via pydantic-settings. Secrets stay in .env and are
read directly with os.getenv() where needed (e.g. panganwatch.db).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import YamlConfigSettingsSource

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "config" / "settings.yaml"


class Settings(BaseSettings):
    """Typed view over config/settings.yaml. Unmodeled keys pass through as dicts."""

    model_config = SettingsConfigDict(yaml_file=str(SETTINGS_PATH), extra="allow")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (YamlConfigSettingsSource(settings_cls),)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
