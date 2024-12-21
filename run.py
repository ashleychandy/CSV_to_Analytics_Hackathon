import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

if __name__ == "__main__":
    import uvicorn
    
    # Create necessary directories
    os.makedirs("data/input", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Run the application
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True) 