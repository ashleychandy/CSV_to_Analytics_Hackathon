import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import tempfile
from datetime import datetime

from src.models.pos_transaction import Base
from src.models.user import User
from src.utils.auth import get_password_hash

@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="session")
def TestingSessionLocal(engine):
    """Create a test database session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db(TestingSessionLocal):
    """Get a test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="session")
def test_users(engine):
    """Create test users."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Create test users with different roles
    users = [
        User(
            username="user1",
            password_hash=get_password_hash("pass1"),
            role="admin",
            is_active=True
        ),
        User(
            username="user2",
            password_hash=get_password_hash("pass2"),
            role="manager",
            is_active=True
        ),
        User(
            username="user3",
            password_hash=get_password_hash("pass3"),
            role="user",
            is_active=True
        )
    ]

    for user in users:
        session.add(user)
    session.commit()

    yield users

    # Clean up
    session.query(User).delete()
    session.commit()
    session.close()

@pytest.fixture
def test_csv_file():
    """Create a temporary test CSV file."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
        f.write("store_code,store_display_name,trans_date,trans_time,trans_no,till_no,net_sales_header_values,quantity\n")
        f.write(f"S001,Store 1,{datetime.now().date()},12:00:00,T001,1,100.00,1\n")
        temp_file = f.name

    yield temp_file

    # Clean up
    os.unlink(temp_file) 