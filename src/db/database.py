from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import logging
import asyncio
from contextlib import asynccontextmanager
from src.models.pos_transaction import Base
from src.config.settings import settings
from typing import Dict, Any, Optional, List
from bson import ObjectId

logger = logging.getLogger(__name__)

# SQLite Configuration
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

# SQLite SessionMaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# MongoDB Client
class MongoDB:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if MongoDB is connected"""
        return self._connected and self.client is not None and self.db is not None and self.collection is not None

    async def ensure_connected(self):
        """Ensure MongoDB connection is established"""
        if not self.is_connected:
            await self.connect()

    async def connect(self):
        """Connect to MongoDB"""
        if self.is_connected:
            return

        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            await self.client.admin.command('ping')  # Test connection
            
            self.db = self.client[settings.mongodb_db]
            self.collection = self.db[settings.mongodb_collection]
            self._connected = True
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            await self.disconnect()
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB"""
        try:
            if self.client is not None:
                self.client.close()
            self.client = None
            self.db = None
            self.collection = None
            self._connected = False
            logger.info("Disconnected from MongoDB")
        except Exception as e:
            logger.error(f"Error during MongoDB disconnect: {str(e)}")

    async def insert_raw_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Insert a raw transaction into MongoDB"""
        try:
            await self.ensure_connected()
            if not self.is_connected:
                raise Exception("MongoDB not connected")
            
            result = await self.collection.insert_one(transaction)
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Failed to insert transaction: {str(e)}")
            return False

    async def get_unprocessed_transactions(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """Get unprocessed transactions from MongoDB"""
        try:
            await self.ensure_connected()
            if not self.is_connected:
                raise Exception("MongoDB not connected")
            
            cursor = self.collection.find({"processed": False}).limit(batch_size)
            return await cursor.to_list(length=batch_size)
        except Exception as e:
            logger.error(f"Failed to get unprocessed transactions: {str(e)}")
            return []

    async def mark_as_processed(self, transaction_ids: List[str]) -> int:
        """Mark transactions as processed"""
        try:
            await self.ensure_connected()
            if not self.is_connected:
                raise Exception("MongoDB not connected")
            
            # Convert string IDs to ObjectId
            object_ids = [ObjectId(id_) for id_ in transaction_ids]
            
            result = await self.collection.update_many(
                {"_id": {"$in": object_ids}},
                {"$set": {"processed": True}}
            )
            logger.info(f"Marked {result.modified_count} transactions as processed")
            return result.modified_count
        except Exception as e:
            logger.error(f"Failed to mark transactions as processed: {str(e)}")
            return 0

    async def delete_all(self) -> bool:
        """Delete all documents in the collection (for testing/cleanup)"""
        try:
            await self.ensure_connected()
            if not self.is_connected:
                raise Exception("MongoDB not connected")
            
            result = await self.collection.delete_many({})
            logger.info(f"Deleted {result.deleted_count} documents from MongoDB")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {str(e)}")
            return False

# Initialize MongoDB client
mongodb = MongoDB()

def init_db():
    """Initialize SQLite database"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get SQLite database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Async SQLite setup for background tasks
ASYNC_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./pos_transactions.db"
async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL)
async_session = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False, 
    autoflush=False
) 