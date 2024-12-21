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
    upload_dir: str = os.path.join(os.getcwd(), "uploads")
    input_dir: str = os.path.join("data", "input")

    # Database settings
    database_url: str = f"sqlite:///{os.path.join(os.getcwd(), 'data', 'app.db')}"
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "pos_etl"
    mongodb_collection: str = "raw_transactions"

    # ETL settings
    batch_size: int = 1000
    sync_interval: int = 300  # 5 minutes

    # Security settings
    secret_key: str = "your-secret-key-here"  # Change in production
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_prefix = "POS_ETL_"
        case_sensitive = False

settings = Settings()

# Ensure required directories exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.input_dir, exist_ok=True)
os.makedirs("logs", exist_ok=True)