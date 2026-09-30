from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
