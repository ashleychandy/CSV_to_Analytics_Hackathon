from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
import os

# Create the FastAPI app
app = FastAPI(
    title="POS Analytics API",
    description="API for POS transaction analytics",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "your-secret-key-here"),
    same_site="lax",
    https_only=True
)

# Mount templates directory
templates = Jinja2Templates(directory="src/templates")

# Import and include the main application routes
try:
    from src.main import app as main_router
    app.include_router(main_router)
except Exception as e:
    import logging
    logging.error(f"Error importing main app: {str(e)}")
    
    @app.get("/")
    async def error_root():
        return {
            "error": "Application initialization error",
            "message": str(e)
        }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"} 