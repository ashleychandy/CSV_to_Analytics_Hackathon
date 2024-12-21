import os
import logging
from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from models.pos_transaction import Base, POSTransaction
from services.etl_service import ETLService
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from typing import List, Dict
from db.database import get_db, mongodb
from config.settings import settings
import asyncio
from fastapi.responses import HTMLResponse, JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/etl.log'),
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")

# Database setup
def init_db():
    """Initialize the database"""
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "sqlite:///./pos_transactions.db")
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    Base.metadata.create_all(bind=engine)
    return engine

# Initialize database and session maker
engine = init_db()
SessionLocal = sessionmaker(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    """Background task to sync data from MongoDB to SQLite periodically"""
    while True:
        try:
            db = next(get_db())
            etl_service = ETLService(db)
            result = await etl_service.sync_service.sync_transactions(settings.batch_size)
            logger.info(f"Periodic sync completed: {result}")
        except Exception as e:
            logger.error(f"Error in periodic sync: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()
        await asyncio.sleep(settings.sync_interval)

@app.on_event("startup")
async def startup_event():
    """Initialize MongoDB connection and start background sync task"""
    try:
        await mongodb.connect()
        asyncio.create_task(sync_data_periodically())
        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection"""
    try:
        await mongodb.disconnect()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Routes
@app.get("/")
async def root(request: Request):
    """Render the dashboard"""
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "status": etl_status.status,
            "active_page": "dashboard"
        }
    )

@app.get("/upload")
async def upload_page(request: Request):
    """Render the upload page"""
    return templates.TemplateResponse(
        "upload.html", 
        {
            "request": request, 
            "status": etl_status.status,
            "active_page": "upload"
        }
    )

@app.get("/transactions")
async def transactions_page(request: Request):
    """Render the transactions page"""
    return templates.TemplateResponse(
        "transactions.html", 
        {
            "request": request, 
            "status": etl_status.status,
            "active_page": "transactions"
        }
    )

@app.get("/analytics")
async def analytics_page(request: Request):
    """Render the analytics page"""
    return templates.TemplateResponse(
        "analytics.html", 
        {
            "request": request, 
            "status": etl_status.status,
            "active_page": "analytics"
        }
    )

@app.get("/api/status")
async def get_status():
    """Get current ETL status"""
    return {
        "status": etl_status.status,
        "processed_count": etl_status.processed_count,
        "processing_time": etl_status.processing_time,
        "last_update": etl_status.last_update.isoformat() if etl_status.last_update else None
    }

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Handle file upload and trigger ETL process"""
    try:
        # Validate file extension
        if not file.filename.lower().endswith('.csv'):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Only CSV files are allowed"}
            )

        # Validate file size
        file_size = 0
        chunk_size = 8192  # 8KB chunks
        content = bytearray()
        
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > settings.max_file_size:
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "message": f"File size exceeds maximum limit of {settings.max_file_size / (1024*1024)}MB"}
                )
            content.extend(chunk)

        # Save file
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_path = os.path.join(settings.upload_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Process file
        try:
            etl_service = ETLService(db)
            result = await etl_service.process_file(file_path)
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "File processed successfully",
                    "details": result
                }
            )
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            # Clean up the file if processing fails
            if os.path.exists(file_path):
                os.remove(file_path)
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Error processing file",
                    "details": str(e)
                }
            )

    except Exception as e:
        logger.error(f"Error handling upload: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal Server Error",
                "details": str(e)
            }
        )

@app.post("/api/process")
async def process_files(db: Session = Depends(get_db)):
    """Process all files in the input directory"""
    try:
        start_time = datetime.now()
        etl_status.update("Processing all files...")
        
        input_dir = "data/input"
        if not os.path.exists(input_dir):
            os.makedirs(input_dir)

        etl_service = ETLService(db)
        processed_count = 0

        for filename in os.listdir(input_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(input_dir, filename)
                etl_service.process_file(file_path)
                processed_count += 1
                etl_status.update(f"Processed {processed_count} files...", count=processed_count)

        processing_time = (datetime.now() - start_time).total_seconds()
        etl_status.update("Completed", time=processing_time)

        return {"message": f"Processed {processed_count} files successfully"}
    except Exception as e:
        etl_status.update(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data")
async def get_data(
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db)
):
    """Get paginated transaction data"""
    offset = (page - 1) * per_page
    total = db.query(POSTransaction).count()
    transactions = db.query(POSTransaction).offset(offset).limit(per_page).all()
    
    return {
        "data": [
            {
                "id": t.id,
                "store_code": t.store_code,
                "store_display_name": t.store_display_name,
                "trans_date": t.trans_date.isoformat(),
                "trans_time": t.trans_time,
                "trans_no": t.trans_no,
                "net_sales_header_values": t.net_sales_header_values,
                "quantity": t.quantity,
                "tender": t.tender
            }
            for t in transactions
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

@app.get("/api/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get transaction analytics"""
    try:
        # Total sales
        total_sales = db.query(func.sum(POSTransaction.net_sales_header_values)).scalar() or 0
        
        # Total transactions
        total_transactions = db.query(POSTransaction).count()
        
        # Sales by tender type
        sales_by_tender = db.query(
            POSTransaction.tender,
            func.count(POSTransaction.id).label('count'),
            func.sum(POSTransaction.net_sales_header_values).label('total')
        ).group_by(POSTransaction.tender).all()
        
        # Sales by store
        sales_by_store = db.query(
            POSTransaction.store_code,
            POSTransaction.store_display_name,
            func.count(POSTransaction.id).label('count'),
            func.sum(POSTransaction.net_sales_header_values).label('total')
        ).group_by(POSTransaction.store_code).all()
        
        return {
            "total_sales": float(total_sales),
            "total_transactions": total_transactions,
            "average_transaction_value": float(total_sales / total_transactions) if total_transactions > 0 else 0,
            "sales_by_tender": [
                {
                    "tender": tender or "Unknown",
                    "count": count,
                    "total": float(total)
                }
                for tender, count, total in sales_by_tender
            ],
            "sales_by_store": [
                {
                    "store_code": store_code,
                    "store_name": store_name,
                    "count": count,
                    "total": float(total)
                }
                for store_code, store_name, count, total in sales_by_store
            ]
        }
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export")
async def export_data(db: Session = Depends(get_db)):
    """Export all transaction data as CSV"""
    try:
        transactions = db.query(POSTransaction).all()
        
        if not transactions:
            raise HTTPException(status_code=404, detail="No data to export")
        
        # Convert to list of dictionaries
        data = [
            {
                "id": t.id,
                "store_code": t.store_code,
                "store_display_name": t.store_display_name,
                "trans_date": t.trans_date.isoformat(),
                "trans_time": t.trans_time,
                "trans_no": t.trans_no,
                "till_no": t.till_no,
                "discount_header": t.discount_header,
                "tax_header": t.tax_header,
                "net_sales_header_values": t.net_sales_header_values,
                "quantity": t.quantity,
                "trans_type": t.trans_type,
                "tender": t.tender,
                "dm_load_date": t.dm_load_date,
                "dm_load_delta_id": t.dm_load_delta_id
            }
            for t in transactions
        ]
        
        return data
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)