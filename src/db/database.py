from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from config.settings import settings
import logging
import asyncio
from contextlib import asynccontextmanager
from models.pos_transaction import Base
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pos_transactions.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# MongoDB setup
class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None
        self._lock = asyncio.Lock()
        self._connection_retries = 3
        self._retry_delay = 2

    async def connect_to_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            async with self._lock:
                if self.client:
                    await self.client.close()
                
                self.client = AsyncIOMotorClient(
                    settings.MONGODB_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000
                )
                self.db = self.client.pos_transactions
                await self.client.admin.command('ping')
                logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"MongoDB connection error: {str(e)}")
            raise

    async def close_mongodb_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("Disconnected from MongoDB")

    @asynccontextmanager
    async def get_connection(self):
        """Get MongoDB connection with automatic reconnection"""
        if not self.client or not self.db:
            await self.connect_to_mongodb()
        try:
            yield self.db
        except Exception as e:
            logger.error(f"MongoDB operation error: {str(e)}")
            raise

mongodb = MongoDB()

# Async SQLAlchemy setup
ASYNC_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./pos_transactions.db"
async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL)
async_session = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False, 
    autoflush=False
)

Base = declarative_base()

# Dependency to get async DB session
async def get_async_db():
    async_session_local = async_session()
    try:
        yield async_session_local
    finally:
        await async_session_local.close() 