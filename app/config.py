"""Environment-based configuration without startup credentials checks."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load optional credentials and the selected API's base URL."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    data_go_kr_key: SecretStr = SecretStr("")
    kspo_base_url: str = ""

    @property
    def key_configured(self) -> bool:
        return bool(self.data_go_kr_key.get_secret_value().strip())


def get_settings() -> Settings:
    """Read settings when needed, rather than at module import."""
    return Settings()
