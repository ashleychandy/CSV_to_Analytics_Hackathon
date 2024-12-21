import os
import logging
from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Depends, BackgroundTasks, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from datetime import datetime, timedelta
import asyncio

from src.models.user import User
from src.models.pos_transaction import POSTransaction
from src.utils.auth import (
    verify_password, create_access_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
)
from src.repositories.user_repository import UserRepository
from src.services.etl_service import ETLService
from src.db.init_db import engine, SessionLocal, get_db, init_database
from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
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
    max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Match token expiry
    same_site="lax",
    https_only=False  # Set to True in production with HTTPS
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/templates")

# Initialize database
engine, SessionLocal = init_database()

# Initialize user repository
def get_user_repository(db: Session = Depends(get_db)):
    """Get user repository with database session."""
    return UserRepository(db)

# Status tracking
class ETLStatus:
    def __init__(self):
        self.status = "Idle"
        self.processed_count = 0
        self.processing_time = 0
        self.last_update = None

    def update(self, status: str, count: int = None, time: float = None):
        self.status = status
        if count is not None:
            self.processed_count = count
        if time is not None:
            self.processing_time = time
        self.last_update = datetime.now()

etl_status = ETLStatus()

# Background sync task
async def sync_data_periodically():
    """Background task to sync data periodically"""
    while True:
        try:
            db = SessionLocal()
            etl_service = ETLService(db)
            result = await etl_service.process_file(
                file_path=None,  # No file path for sync
                user_id=None  # No user ID for sync
            )
            logger.info(f"Periodic sync completed: {result}")
        except Exception as e:
            logger.error(f"Error in periodic sync: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()
        await asyncio.sleep(settings.sync_interval)

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    try:
        asyncio.create_task(sync_data_periodically())
        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

# Route handlers
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

@app.get("/logout")
async def logout(request: Request):
    """Logout endpoint."""
    # Clear session
    request.session.clear()
    
    # Create response with redirect
    response = RedirectResponse(url="/login", status_code=303)
    
    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("session")
    
    return response

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Upload page."""
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "user": request.session["user"],
            "settings": {
                "max_file_size": settings.max_file_size
            }
        }
    )

@app.post("/api/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Handle file upload."""
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Save file
        file_path = os.path.join(settings.upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process file
        etl_service = ETLService(db)
        result = await etl_service.process_file(
            file_path=file_path,
            user_id=request.session["user"]["id"]
        )
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/api/data")
async def get_data(
    request: Request,
    page: int = 1,
    per_page: int = 10,
    start_date: str = None,
    end_date: str = None,
    store: str = None,
    tender: str = None,
    amount_range: str = None,
    db: Session = Depends(get_db)
):
    """Get paginated transaction data."""
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get user's transactions with filtering
        query = db.query(POSTransaction)
        query = get_user_data_filter(request.session["user"], query, db)
        
        # Apply date range filter
        if start_date:
            query = query.filter(POSTransaction.trans_date >= datetime.strptime(start_date, "%Y-%m-%d"))
        if end_date:
            query = query.filter(POSTransaction.trans_date <= datetime.strptime(end_date, "%Y-%m-%d"))
        
        # Apply store filter
        if store:
            query = query.filter(POSTransaction.store_display_name == store)
        
        # Apply tender filter
        if tender:
            query = query.filter(POSTransaction.tender == tender)
        
        # Apply amount range filter
        if amount_range:
            if amount_range == "0-50":
                query = query.filter(POSTransaction.net_sales_header_values.between(0, 50))
            elif amount_range == "51-100":
                query = query.filter(POSTransaction.net_sales_header_values.between(51, 100))
            elif amount_range == "101-500":
                query = query.filter(POSTransaction.net_sales_header_values.between(101, 500))
            elif amount_range == "501+":
                query = query.filter(POSTransaction.net_sales_header_values >= 501)
        
        total = query.count()
        transactions = query.order_by(POSTransaction.trans_date.desc(), POSTransaction.trans_time.desc())\
                          .offset((page - 1) * per_page)\
                          .limit(per_page)\
                          .all()
        
        return {
            "data": [t.__dict__ for t in transactions],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics")
async def get_analytics(request: Request, db: Session = Depends(get_db)):
    """Get analytics data."""
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Base query with user filtering
        query = db.query(POSTransaction)
        query = get_user_data_filter(request.session["user"], query, db)
        
        # Calculate total sales and transactions
        totals = query.with_entities(
            func.sum(POSTransaction.net_sales_header_values).label("total_sales"),
            func.count().label("total_transactions"),
            func.sum(POSTransaction.quantity).label("total_items"),
            func.avg(POSTransaction.net_sales_header_values).label("avg_transaction_value")
        ).first()
        
        # Sales by tender type
        sales_by_tender = (
            query.with_entities(
                POSTransaction.tender,
                func.sum(POSTransaction.net_sales_header_values).label("total"),
                func.count().label("count")
            )
            .group_by(POSTransaction.tender)
            .all()
        )
        
        # Sales by store
        sales_by_store = (
            query.with_entities(
                POSTransaction.store_display_name,
                func.sum(POSTransaction.net_sales_header_values).label("total"),
                func.count().label("transaction_count"),
                func.sum(POSTransaction.quantity).label("item_count")
            )
            .group_by(POSTransaction.store_display_name)
            .all()
        )
        
        # Sales by date
        sales_by_date = (
            query.with_entities(
                POSTransaction.trans_date,
                func.sum(POSTransaction.net_sales_header_values).label("total"),
                func.count().label("transaction_count")
            )
            .group_by(POSTransaction.trans_date)
            .order_by(POSTransaction.trans_date.desc())
            .limit(30)  # Last 30 days
            .all()
        )
        
        # Calculate percentages for tender types
        total_sales = float(totals.total_sales or 0)
        tender_data = [
            {
                "tender": t.tender or "Unknown",
                "total": float(t.total or 0),
                "count": t.count,
                "percentage": (float(t.total or 0) / total_sales * 100) if total_sales > 0 else 0
            }
            for t in sales_by_tender
        ]
        
        # Calculate store performance metrics
        store_data = [
            {
                "store": s.store_display_name,
                "total_sales": float(s.total or 0),
                "transaction_count": s.transaction_count,
                "item_count": s.item_count,
                "avg_transaction": float(s.total or 0) / s.transaction_count if s.transaction_count > 0 else 0,
                "items_per_transaction": s.item_count / s.transaction_count if s.transaction_count > 0 else 0
            }
            for s in sales_by_store
        ]
        
        # Format daily sales data
        daily_data = [
            {
                "date": d.trans_date.strftime("%Y-%m-%d"),
                "total": float(d.total or 0),
                "transaction_count": d.transaction_count,
                "avg_transaction": float(d.total or 0) / d.transaction_count if d.transaction_count > 0 else 0
            }
            for d in sales_by_date
        ]
        
        return {
            "summary": {
                "total_sales": float(totals.total_sales or 0),
                "total_transactions": totals.total_transactions,
                "total_items": totals.total_items,
                "avg_transaction_value": float(totals.avg_transaction_value or 0),
                "items_per_transaction": (totals.total_items / totals.total_transactions) 
                    if totals.total_transactions > 0 else 0
            },
            "sales_by_tender": tender_data,
            "sales_by_store": store_data,
            "daily_sales": daily_data
        }
    except Exception as e:
        logger.error(f"Error fetching analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics page."""
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "user": request.session["user"]}
    )

@app.get("/transactions", response_class=HTMLResponse)
async def transactions_page(request: Request):
    """Transactions page."""
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        "transactions.html",
        {"request": request, "user": request.session["user"]}
    )

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": request.session["user"],
            "settings": {
                "batch_size": settings.batch_size,
                "sync_interval": settings.sync_interval,
                "max_file_size": settings.max_file_size
            }
        }
    )

@app.post("/api/settings/password")
async def update_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Update user password."""
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    user = user_repository.get_by_username(request.session["user"]["username"])
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Update password
    user.password_hash = get_password_hash(new_password)
    user_repository.update(user)
    
    return {"message": "Password updated successfully"}

@app.post("/api/settings/system")
async def update_system_settings(
    request: Request,
    batch_size: int = Form(...),
    sync_interval: int = Form(...),
    max_file_size: int = Form(...)
):
    """Update system settings."""
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if request.session["user"]["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Validate settings
    if batch_size < 1 or batch_size > 10000:
        raise HTTPException(status_code=400, detail="Invalid batch size")
    
    if sync_interval < 60 or sync_interval > 3600:
        raise HTTPException(status_code=400, detail="Invalid sync interval")
    
    if max_file_size < 1024 * 1024 or max_file_size > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Invalid file size")
    
    # Update settings
    settings.batch_size = batch_size
    settings.sync_interval = sync_interval
    settings.max_file_size = max_file_size
    
    return {"message": "System settings updated successfully"}

@app.post("/api/data/clear")
async def clear_data(request: Request, db: Session = Depends(get_db)):
    """Clear all transaction data for the user."""
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get query with user filter
        query = db.query(POSTransaction)
        query = get_user_data_filter(request.session["user"], query, db)
        
        # Delete filtered records
        deleted_count = query.delete(synchronize_session=False)
        db.commit()
        
        return {
            "status": "success",
            "records_deleted": deleted_count,
            "message": f"Successfully deleted {deleted_count} records"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/uploads/history")
async def get_upload_history(request: Request, db: Session = Depends(get_db)):
    """Get upload history for the user."""
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Group by load date and get counts
        query = db.query(
            POSTransaction.dm_load_date,
            func.count().label('record_count'),
            func.sum(POSTransaction.net_sales_header_values).label('total_sales')
        )
        
        # Filter by user_id
        query = get_user_data_filter(request.session["user"], query, db)
        
        history = query.group_by(POSTransaction.dm_load_date)\
                      .order_by(POSTransaction.dm_load_date.desc())\
                      .all()
        
        return {
            "history": [
                {
                    "upload_date": h.dm_load_date.isoformat(),
                    "record_count": h.record_count,
                    "total_sales": float(h.total_sales) if h.total_sales else 0.0
                }
                for h in history
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching upload history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))