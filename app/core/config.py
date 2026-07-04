from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    Database_url: str = ""
    JWT_ALGORITHM: str = ""
    JWT_SECRET_KEY: str = ""
    JWT_DEFAULT_EXP_MINUTES: int = 30
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    ELASTIC_URL: str = "http://elasticsearch:9200"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    VERIFICATION_BASE_URL: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Setting()
