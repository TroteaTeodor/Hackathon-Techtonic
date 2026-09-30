from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Auth. SESSION_SECRET has no default on purpose: the app refuses to start without one.
    session_secret: str
    session_hours: int = 8
    cookie_secure: bool = False
    demo_password: str | None = None

    # Gemini: Vertex AI (service account) when GOOGLE_GENAI_USE_VERTEXAI=true, else an AI Studio key.
    ai_enabled: bool = True
    google_genai_use_vertexai: bool = False
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    google_application_credentials: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: float = 10

    # Scale-view assumptions (shown in the UI next to the projection).
    price_per_million_input_tokens_eur: float = 0.30
    price_per_million_output_tokens_eur: float = 2.50
    estimated_input_tokens_per_analysis: int = 1650
    estimated_output_tokens_per_analysis: int = 200
    projection_customers: int = 2_300_000
    daily_reevaluation_rate: float = 0.05

    @field_validator("session_secret")
    @classmethod
    def secret_is_long_enough(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SESSION_SECRET must be at least 32 characters")
        return value


settings = Settings()
