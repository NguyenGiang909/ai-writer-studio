from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Writer Studio"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./writer.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-insecure-key-change-me"
    allow_fake_provider: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
