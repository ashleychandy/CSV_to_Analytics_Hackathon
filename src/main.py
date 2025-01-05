import os
import logging
from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Depends, APIRouter, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from datetime import datetime
from src.models.user import User
from src.models.pos_transaction import POSTransaction
from src.utils.auth import (
    verify_password, create_access_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
)
from src.repositories.user_repository import UserRepository
from src.services.etl_service import ETLService
from src.db.init_db import get_db
from src.config.settings import settings

# Configure logging for Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI router instead of app
app = APIRouter()

# Initialize templates
templates = Jinja2Templates(directory="src/templates")

def get_user_repository(db: Session = Depends(get_db)):
    """Get user repository with database session."""
    return UserRepository(db)

def get_user_data_filter(user: dict, query, db: Session):
    """Apply user-specific data filter to query."""
    if user["role"] == "admin":
        # Admin can see all data
        return query
    elif user["role"] == "manager":
        # Manager can see their own data and data from regular users
        return query.filter(
            or_(
                POSTransaction.user_id == user["id"],
                POSTransaction.user_id.in_(
                    db.query(User.id).filter(User.role == "user")
                )
            )
        )
    else:
        # Regular users can only see their own data
        return query.filter(POSTransaction.user_id == user["id"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint that redirects to login if not authenticated."""
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": request.session["user"]}
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    if "user" in request.session:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    user_repository: UserRepository = Depends(get_user_repository)
):
    """Login endpoint."""
    try:
        # Clear any existing session
        request.session.clear()
        
        user = user_repository.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid username or password"},
                status_code=401
            )

        # Create session
        request.session["user"] = {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role}
        )
        
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("access_token")  # Clear any existing token
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax"
        )
        return response
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "An error occurred during login"},
            status_code=500
        )

# ... Rest of your routes (upload, analytics, etc.) ...

# Add a health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}