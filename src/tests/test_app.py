import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import tempfile
from datetime import datetime

from src.main import app
from src.models.pos_transaction import Base
from src.db.init_db import get_db
from src.config.settings import settings

# Create a temporary database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_read_main():
    """Test that the main page redirects to login when not authenticated."""
    response = client.get("/")
    assert response.status_code == 303  # Redirect
    assert response.headers["location"] == "/login"

def test_login_page():
    """Test that the login page loads correctly."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.content

def test_login():
    """Test the login functionality."""
    response = client.post(
        "/login",
        data={"username": "user1", "password": "pass1"}
    )
    assert response.status_code == 303  # Redirect
    assert response.headers["location"] == "/"

def test_upload_file():
    """Test file upload functionality."""
    # First login
    client.post("/login", data={"username": "user1", "password": "pass1"})
    
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
        f.write("store_code,store_display_name,trans_date,trans_time,trans_no,till_no,net_sales_header_values,quantity\n")
        f.write(f"S001,Store 1,{datetime.now().date()},12:00:00,T001,1,100.00,1\n")
        temp_file = f.name

    try:
        # Upload the file
        with open(temp_file, 'rb') as f:
            response = client.post(
                "/api/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    finally:
        os.unlink(temp_file)

def test_get_data():
    """Test data retrieval functionality."""
    # First login
    client.post("/login", data={"username": "user1", "password": "pass1"})
    
    response = client.get("/api/data")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data

def test_get_analytics():
    """Test analytics functionality."""
    # First login
    client.post("/login", data={"username": "user1", "password": "pass1"})
    
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "total_sales" in data
    assert "total_transactions" in data
    assert "sales_by_tender" in data
    assert "sales_by_store" in data

def test_unauthorized_access():
    """Test that unauthorized access is properly handled."""
    response = client.get("/api/data")
    assert response.status_code == 401  # Unauthorized

def test_logout():
    """Test logout functionality."""
    # First login
    client.post("/login", data={"username": "user1", "password": "pass1"})
    
    # Then logout
    response = client.get("/logout")
    assert response.status_code == 303  # Redirect
    assert response.headers["location"] == "/login"
    
    # Verify we can't access protected routes
    response = client.get("/api/data")
    assert response.status_code == 401  # Unauthorized 