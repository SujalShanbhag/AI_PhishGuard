import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "AI PhishGuard"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str = "veritas-ai-secure-secret-key-32-chars-minimum-needed!"

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'veritas.db'}"

    # JWT Authentication
    JWT_SECRET_KEY: str = "veritas-jwt-super-secret-key-must-be-at-least-32-chars!"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # File Upload limits & directories
    MAX_IMAGE_SIZE_MB: int = 25

    UPLOAD_DIR: str = str(BASE_DIR / "data" / "uploads")
    REPORTS_DIR: str = str(BASE_DIR / "data" / "reports")
    IDENTITY_DIR: str = str(BASE_DIR / "data" / "identity")
    MODELS_DIR: str = str(BASE_DIR / "data" / "models")
    EVALUATIONS_DIR: str = str(BASE_DIR / "data" / "evaluations")
    EVIDENCE_DIR: str = str(BASE_DIR / "data" / "evidence")
    REDACTED_DIR: str = str(BASE_DIR / "data" / "redacted")
    DATASETS_DIR: str = str(BASE_DIR / "data" / "datasets")
    SYNTHETIC_DIR: str = str(BASE_DIR / "data" / "synthetic_datasets")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    LOGIN_RATE_LIMIT: int = 10
    LOGIN_RATE_LIMIT_WINDOW: int = 300

    # Model Configuration
    DEEPFAKE_MODEL_PATH: str = str(BASE_DIR / "data" / "models" / "veritas_detector.pt")
    DEEPFAKE_MODEL_ARCH: str = "efficientnet_b4"
    FACE_DETECTION_BACKEND: str = "opencv"
    GRADCAM_ENABLED: bool = True

    # Gemini AI Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Decision thresholds
    SUSPICIOUS_THRESHOLD: float = 0.65
    AUTHENTIC_THRESHOLD: float = 0.35

    # CORS
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    # Cookie Security
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    def get_cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def get_model_path(self) -> str:
        if not self.DEEPFAKE_MODEL_PATH or not self.DEEPFAKE_MODEL_PATH.strip():
            fallback = BASE_DIR / "data" / "models" / "veritas_detector.pt"
            return str(fallback) if fallback.exists() else ""
        p = Path(self.DEEPFAKE_MODEL_PATH)
        if not p.is_absolute():
            p = BASE_DIR / p
        return str(p) if p.exists() else ""

    def ensure_directories(self) -> None:
        for path_str in [
            self.UPLOAD_DIR,
            self.REPORTS_DIR,
            self.IDENTITY_DIR,
            self.MODELS_DIR,
            self.EVALUATIONS_DIR,
            self.EVIDENCE_DIR,
            self.REDACTED_DIR,
            self.DATASETS_DIR,
            self.SYNTHETIC_DIR,
        ]:
            Path(path_str).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
