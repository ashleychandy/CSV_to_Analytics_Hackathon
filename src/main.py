import os
import logging
from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models.pos_transaction import Base, POSTransaction
from services.etl_service import ETLService
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime

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
app = FastAPI()

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

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()

# Routes
@app.get("/")
async def root(request: Request):
    """Redirect to dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request, "status": etl_status.status})

@app.get("/dashboard")
async def dashboard(request: Request):
    """Show ETL dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request, "status": etl_status.status})

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
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload and process a CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    try:
        # Save the file
        file_path = os.path.join("data", "input", file.filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Process the file
        start_time = datetime.now()
        etl_status.update("Processing file...")
        
        etl_service = ETLService(db)
        etl_service.process_file(file_path)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        etl_status.update("Completed", time=processing_time)

        return {"message": "File processed successfully"}
    except Exception as e:
        etl_status.update(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)