from pydantic_settings import BaseSettings
from typing import Optional, Set
import os

class Settings(BaseSettings):
    # SQLite settings
    database_url: str = "sqlite:///./pos_transactions.db"
    
    # MongoDB settings
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_uri: str = "mongodb://localhost:27017"  # For backward compatibility
    mongodb_db: str = "pos_etl"
    mongodb_collection: str = "raw_transactions"
    
    # API settings
    api_title: str = "POS ETL Dashboard"
    api_description: str = "API for managing POS transaction ETL processes"
    api_version: str = "1.0.0"
    api_port: int = 8000
    api_username: str = "admin"
    api_password: str = "admin"
    debug: bool = True
    
    # File upload settings
    upload_dir: str = "uploads"
    allowed_extensions: Set[str] = {"csv"}
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # ETL settings
    batch_size: int = 1000
    sync_interval: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)