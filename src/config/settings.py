from pydantic_settings import BaseSettings
from typing import Optional, Set
import os
from pathlib import Path

class Settings(BaseSettings):
    # API settings
    api_title: str = "POS Analytics API"
    api_description: str = "API for POS transaction analytics"
    api_version: str = "1.0.0"

    # File upload settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: Set[str] = {".csv"}
    upload_dir: str = "/tmp/uploads"  # Use /tmp for Vercel
    input_dir: str = "/tmp/data/input"  # Use /tmp for Vercel

    # Database settings
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///tmp/app.db")
    mongodb_url: str = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db: str = os.environ.get("MONGODB_DB", "pos_etl")
    mongodb_collection: str = os.environ.get("MONGODB_COLLECTION", "raw_transactions")

    # ETL settings
    batch_size: int = int(os.environ.get("BATCH_SIZE", "1000"))
    sync_interval: int = int(os.environ.get("SYNC_INTERVAL", "300"))  # 5 minutes

    # Security settings
    secret_key: str = os.environ.get("SECRET_KEY", "your-secret-key-here")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "30"))

    class Config:
        env_prefix = "POS_ETL_"
        case_sensitive = False

settings = Settings()

# Create directories only in development environment
if not os.environ.get("VERCEL"):
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.input_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
