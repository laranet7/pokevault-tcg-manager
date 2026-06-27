from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PokeVault TCG"
    api_prefix: str = "/api"
    terms_version: str = "1.0"
    database_url: str = "postgresql+asyncpg://pokevault:pokevault@db:5432/pokevault"
    pokemon_tcg_api_url: str = "https://api.pokemontcg.io/v2"
    pokemon_tcg_api_key: str | None = None
    tcgdex_api_url: str = "https://api.tcgdex.net/v2"
    tcgdex_api_language: str = "en"
    media_root: str = "./media"
    media_cards_dir: str = "cards"
    cors_origins: str = "http://localhost:8080"
    seed_default_admin: bool = True
    auth_secret_key: str = "change-me-with-a-long-random-secret"
    auth_token_ttl_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
