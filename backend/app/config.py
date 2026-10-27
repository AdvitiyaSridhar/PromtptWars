import os
from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import model_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "FairShift"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./fairshift.db"
    
    # Auth & Tokens
    JWT_SECRET_KEY: str = "fairshift-local-jwt-change-before-deploy"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # QR Signing Key
    SITE_QR_SECRET: str = "fairshift-local-qr-change-before-deploy"
    
    # Storage
    STORAGE_BACKEND: str = "local"  # "local" or "gcs"
    LOCAL_UPLOAD_DIR: str = "./uploads"
    GCS_BUCKET_NAME: Optional[str] = None
    GCS_SERVICE_ACCOUNT_JSON: Optional[str] = None
    
    # Environment
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        extra = "ignore"

    @model_validator(mode="after")
    def require_production_secrets(self):
        if self.ENVIRONMENT.lower() not in ("development", "test"):
            secrets = (self.JWT_SECRET_KEY, self.SITE_QR_SECRET)
            if any(secret.startswith("fairshift-local-") or len(secret) < 32 for secret in secrets):
                raise ValueError("JWT_SECRET_KEY and SITE_QR_SECRET must be set to unique production secrets.")
            if self.JWT_SECRET_KEY == self.SITE_QR_SECRET:
                raise ValueError("JWT_SECRET_KEY and SITE_QR_SECRET must be different values.")
            if not self.DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
                raise ValueError("Production deployments must use PostgreSQL, not local SQLite.")
            if self.STORAGE_BACKEND != "gcs" or not self.GCS_BUCKET_NAME:
                raise ValueError("Production deployments require STORAGE_BACKEND=gcs and GCS_BUCKET_NAME.")
            if os.getenv("VERCEL") and not self.GCS_SERVICE_ACCOUNT_JSON:
                raise ValueError("Vercel deployments require GCS_SERVICE_ACCOUNT_JSON for private evidence storage.")
        return self

settings = Settings()
