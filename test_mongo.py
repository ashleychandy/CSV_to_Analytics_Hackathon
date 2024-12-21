import sys
import os
sys.path.append(os.path.abspath("."))

import asyncio
import logging
from src.db.database import mongodb
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mongodb():
    try:
        # Test connection
        logger.info("Testing MongoDB connection...")
        await mongodb.connect()
        
        # Test insert
        logger.info("Testing insert operation...")
        test_transaction = {
            "store_code": "TEST001",
            "store_display_name": "Test Store",
            "trans_date": datetime.now().isoformat(),
            "trans_time": "12:00:00",
            "trans_no": "T123",
            "till_no": "1",
            "discount_header": 0.0,
            "tax_header": 0.5,
            "net_sales_header_values": 100.0,
            "quantity": 1,
            "trans_type": 1,
            "id_key": 12345,
            "tender": "CASH",
            "dm_load_date": "2024-01-01",
            "dm_load_delta_id": 1,
            "processed": False
        }
        
        success = await mongodb.insert_raw_transaction(test_transaction)
        if success:
            logger.info("Successfully inserted test transaction")
        else:
            logger.error("Failed to insert test transaction")
        
        # Test retrieval
        logger.info("Testing retrieval of unprocessed transactions...")
        unprocessed = await mongodb.get_unprocessed_transactions(batch_size=10)
        logger.info(f"Found {len(unprocessed)} unprocessed transactions")
        
        if unprocessed:
            # Test marking as processed
            transaction_ids = [str(transaction['_id']) for transaction in unprocessed]
            logger.info("Testing marking transactions as processed...")
            processed_count = await mongodb.mark_as_processed(transaction_ids)
            logger.info(f"Marked {processed_count} transactions as processed")
        
        # Verify processed state
        logger.info("Verifying processed state...")
        remaining_unprocessed = await mongodb.get_unprocessed_transactions(batch_size=10)
        logger.info(f"Remaining unprocessed transactions: {len(remaining_unprocessed)}")
        
        # Clean up
        logger.info("Cleaning up test data...")
        if mongodb.db is not None and mongodb.collection is not None:
            await mongodb.collection.delete_many({"store_code": "TEST001"})
            logger.info("Test data cleaned up")
        
        await mongodb.disconnect()
        logger.info("MongoDB test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during MongoDB test: {str(e)}")
        raise
    finally:
        if mongodb.client is not None:
            await mongodb.disconnect()

if __name__ == "__main__":
    asyncio.run(test_mongodb()) 