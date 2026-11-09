# 용도: 로컬 환경변수를 읽고 서버·Gemini 설정을 검증한다.
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    llm_provider: str = "gemini"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = Field(default="gemini-3.1-flash-lite", pattern=r"^[a-zA-Z0-9_.-]+$")
    llm_timeout_seconds: float = Field(default=45, ge=1, le=120)
    max_input_chars: int = Field(default=10000, ge=1, le=10000)
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    max_requests_per_minute: int = Field(default=10, ge=1, le=100)
    max_requests_per_day: int = Field(default=100, ge=1, le=1000)


def settings() -> Settings:
    return Settings()
