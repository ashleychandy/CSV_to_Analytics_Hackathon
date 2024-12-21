from fastapi import FastAPI, Depends, Request, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.services.etl_service import ETLService
from src.utils.status_monitor import ProcessingMonitor
from datetime import datetime
from sqlalchemy.orm import Session
from src.db.database import SessionLocal, mongodb
import logging
from src.utils.csv_parser import POSDataParser

logger = logging.getLogger(__name__)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()
monitor = ProcessingMonitor()
etl_service = ETLService(monitor)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")

@app.on_event("startup")
async def startup_db():
    await mongodb.connect_to_mongodb()
    logger.info("Connected to MongoDB")

@app.on_event("shutdown")
async def shutdown_db():
    await mongodb.close_mongodb_connection()

@app.get("/dashboard")
async def dashboard(request: Request):
    """Web interface for monitoring ETL processes"""
    status_data = monitor.get_status()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "status": status_data["status"]
    })

@app.post("/api/v1/etl/run")
async def run_etl(db: Session = Depends(get_db)):
    """Trigger ETL pipeline"""
    start_time = datetime.utcnow()
    try:
        # Extract
        raw_data = await etl_service.extract_from_mongodb()
        
        # Transform
        transformed_data = await etl_service.transform_data(raw_data)
        monitor.increment_processed(len(transformed_data))
        
        # Load
        await etl_service.load_to_sql(transformed_data, db)
        
        # Update processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        monitor.update_processing_time(processing_time)
        
        monitor.update_status("ETL process completed")
        return {"status": "success", "message": "ETL process completed"}
    except Exception as e:
        monitor.update_status(f"Error: {str(e)}")
        logger.error(f"ETL process failed: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    try:
        # Test MongoDB connection
        await mongodb.client.admin.command('ping')
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }

@app.get("/api/v1/status")
async def get_status():
    status_data = monitor.get_status()
    return {
        "status": status_data["status"],
        "processed_count": status_data["processed_count"],
        "processing_time": status_data["processing_time"],
        "last_update": status_data["last_update"].isoformat() if status_data["last_update"] else None
    }

@app.post("/api/v1/transactions/upload")
async def upload_transactions(file: UploadFile = File(...)):
    """Upload transactions from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
        
    try:
        monitor.update_status("Uploading transactions...")
        content = await file.read()
        try:
            lines = content.decode('utf-8').splitlines()
        except UnicodeDecodeError:
            lines = content.decode('latin-1').splitlines()
        
        # Skip header if present
        if lines and not lines[0].strip().startswith('BIAL') and not lines[0].strip().startswith('TFSB'):
            lines = lines[1:]
        
        transactions = []
        parser = POSDataParser()
        errors = []
        
        for i, line in enumerate(lines, 1):
            if line.strip():
                try:
                    parsed_data = parser.parse_line(line)
                    if not parsed_data['store_code'].startswith(('BIAL', 'TFSB')):
                        errors.append(f"Line {i}: Invalid store code format")
                        continue
                    transactions.append(parsed_data)
                except Exception as e:
                    errors.append(f"Line {i}: {str(e)}")
        
        if not transactions:
            raise HTTPException(status_code=400, detail="No valid transactions found in file")
            
        if transactions:
            collection = mongodb.db.transactions
            result = await collection.insert_many(transactions)
            monitor.increment_processed(len(result.inserted_ids))
        
        response = {
            "status": "success" if not errors else "partial_success",
            "message": f"Processed {len(transactions)} transactions",
            "transaction_count": len(transactions)
        }
        
        if errors:
            response["errors"] = errors
            response["error_count"] = len(errors)
            
        return response
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        monitor.update_status(f"Upload error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))