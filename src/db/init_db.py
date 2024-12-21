import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings
from src.models.user import User
from src.models.pos_transaction import POSTransaction
from src.utils.auth import get_password_hash
from src.db.base import Base

logger = logging.getLogger(__name__)

def init_test_users(db):
    """Initialize test users if they don't exist."""
    try:
        # Check if users exist
        if db.query(User).count() == 0:
            # Create test users
            test_users = [
                User(
                    username="user1",
                    password_hash=get_password_hash("pass1"),
                    role="user"
                ),
                User(
                    username="user2",
                    password_hash=get_password_hash("pass2"),
                    role="user"
                ),
                User(
                    username="user3",
                    password_hash=get_password_hash("pass3"),
                    role="admin"
                )
            ]
            
            # Add users to database
            for user in test_users:
                db.add(user)
            
            db.commit()
            logger.info("Test users initialized successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing test users: {str(e)}")
        raise

def init_database():
    """Initialize database connection and create tables."""
    try:
        # Create database directory if it doesn't exist
        db_path = settings.database_url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # Create engine
        engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        )
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Initialize test users
        db = SessionLocal()
        try:
            # Test connection
            db.execute(text("SELECT 1"))
            
            # Initialize test users
            init_test_users(db)
            
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error testing database connection: {str(e)}")
            raise
        finally:
            db.close()
        
        return engine, SessionLocal
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database and create global SessionLocal
engine, SessionLocal = init_database()

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize database
    init_database()
    logger.info("Database initialization script completed") 