import sys
import os
sys.path.append(os.path.abspath("."))

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.db.database import mongodb, get_db
from src.services.etl_service import ETLService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sample_data(num_records=1000):
    """Generate sample POS transaction data"""
    np.random.seed(42)
    
    # Generate dates for the last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    dates = pd.date_range(start=start_date, end=end_date, freq='H')
    
    # Store information
    stores = [
        ('ST001', 'Downtown Store'),
        ('ST002', 'Mall Store'),
        ('ST003', 'Airport Store'),
        ('ST004', 'Station Store')
    ]
    
    # Generate data
    data = []
    for i in range(num_records):
        store = stores[np.random.randint(0, len(stores))]
        trans_date = dates[np.random.randint(0, len(dates))]
        
        record = {
            'STORE_CODE': store[0],
            'STORE_DISPLAY_NAME': store[1],
            'TRANS_DATE': trans_date.strftime('%Y-%m-%d'),
            'TRANS_TIME': trans_date.strftime('%H:%M:%S'),
            'TRANS_NO': f'T{i+1:06d}',
            'TILL_NO': f'{np.random.randint(1, 6)}',
            'DISCOUNT_HEADER': round(np.random.uniform(0, 50), 2),
            'TAX_HEADER': round(np.random.uniform(5, 15), 2),
            'NET_SALES_HEADER_VALUES': round(np.random.uniform(10, 1000), 2),
            'quantity': np.random.randint(1, 10),
            'TRANS_TYPE': np.random.randint(1, 4),
            'ID_KEY': i + 1,
            'TENDER': np.random.choice(['CASH', 'CARD', 'MOBILE', 'NULL'], p=[0.3, 0.4, 0.2, 0.1]),
            'DM_LOAD_DATE': datetime.now().strftime('%Y-%m-%d'),
            'DM_LOAD_DELTA_ID': np.random.randint(1000, 9999)
        }
        data.append(record)
    
    return pd.DataFrame(data)

async def test_etl_pipeline():
    try:
        # Generate sample data
        logger.info("Generating sample data...")
        df = generate_sample_data()
        
        # Save to CSV
        csv_path = "data/input/sample_transactions.csv"
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved {len(df)} records to {csv_path}")
        
        # Connect to MongoDB
        logger.info("Connecting to MongoDB...")
        await mongodb.connect()
        
        # Initialize ETL service
        db = next(get_db())
        etl_service = ETLService(db)
        
        # Process the file
        logger.info("Processing file through ETL pipeline...")
        result = await etl_service.process_file(csv_path)
        logger.info(f"ETL process results: {result}")
        
        # Verify data in MongoDB
        unprocessed = await mongodb.get_unprocessed_transactions(batch_size=1000)
        logger.info(f"Unprocessed records in MongoDB: {len(unprocessed)}")
        
        # Verify data in SQLite
        from src.models.pos_transaction import POSTransaction
        sqlite_count = db.query(POSTransaction).count()
        logger.info(f"Records in SQLite: {sqlite_count}")
        
        # Get some statistics
        if sqlite_count > 0:
            # Total sales by store
            store_sales = db.query(
                POSTransaction.store_code,
                POSTransaction.store_display_name,
                func.sum(POSTransaction.net_sales_header_values).label('total_sales')
            ).group_by(POSTransaction.store_code).all()
            
            logger.info("\nSales by Store:")
            for store in store_sales:
                logger.info(f"{store.store_display_name}: ${store.total_sales:,.2f}")
            
            # Sales by tender type
            tender_sales = db.query(
                POSTransaction.tender,
                func.sum(POSTransaction.net_sales_header_values).label('total_sales')
            ).group_by(POSTransaction.tender).all()
            
            logger.info("\nSales by Tender Type:")
            for tender in tender_sales:
                logger.info(f"{tender.tender or 'Unknown'}: ${tender.total_sales:,.2f}")
        
        # Clean up
        logger.info("\nCleaning up test data...")
        if mongodb.db is not None and mongodb.collection is not None:
            await mongodb.collection.delete_many({})
            logger.info("MongoDB data cleaned up")
        
        db.query(POSTransaction).delete()
        db.commit()
        logger.info("SQLite data cleaned up")
        
        # Clean up CSV
        os.remove(csv_path)
        logger.info("CSV file cleaned up")
        
        logger.info("ETL pipeline test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during ETL pipeline test: {str(e)}")
        raise
    finally:
        if mongodb.client is not None:
            await mongodb.disconnect()
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    from sqlalchemy import func
    asyncio.run(test_etl_pipeline()) 