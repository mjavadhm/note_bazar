from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = ""
    api_base_url: str = "http://api:8000"
    api_secret: str = "dev-secret"
    admin_telegram_ids: str = ""
    redis_url: str = "redis://localhost:6379/0"
    miniapp_url: str = ""  # آدرس HTTPS سایت — برای دکمه «مطالعه آنلاین»

    @property
    def admin_ids(self) -> set[int]:
        return {int(x) for x in self.admin_telegram_ids.split(",") if x.strip().isdigit()}


settings = Settings()
