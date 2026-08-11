from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = ""
    api_secret: str = "dev-secret"
    admin_telegram_ids: str = ""
    commission_percent: int = 20

    database_url: str = "postgresql+psycopg://notebazar:notebazar@localhost:5432/notebazar"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_bucket: str = "notebazar"

    telegram_file_api: str = "https://api.telegram.org"

    @property
    def admin_ids(self) -> set[int]:
        return {int(x) for x in self.admin_telegram_ids.split(",") if x.strip().isdigit()}


settings = Settings()
