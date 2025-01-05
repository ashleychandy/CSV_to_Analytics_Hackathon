import os
import logging
from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from src.models.user import User
from src.models.pos_transaction import POSTransaction
from src.utils.auth import verify_password, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from src.repositories.user_repository import UserRepository
from src.services.etl_service import ETLService
from src.db.init_db import engine, SessionLocal, get_db, init_database
from src.config.settings import settings

# Configure logging to use print for Vercel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="session",
    max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    same_site="lax",
    https_only=True  # Enable HTTPS only for production
)

# Initialize templates
templates = Jinja2Templates(directory="src/templates")

# Initialize database
try:
    engine, SessionLocal = init_database()
except Exception as e:
    logger.error(f"Database initialization error: {str(e)}")
    # Continue without database in serverless environment

# Initialize user repository
def get_user_repository(db: Session = Depends(get_db)):
    return UserRepository(db)

# ... existing code ...