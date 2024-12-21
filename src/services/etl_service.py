import pandas as pd
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from src.models.pos_transaction import POSTransaction
from src.db.database import mongodb
from src.services.data_sync_service import DataSyncService
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)

class ETLService:
    def __init__(self, db: Session):
        self.db = db
        self.sync_service = DataSyncService(db)

    def extract_from_csv(self, file_path: str) -> pd.DataFrame:
        """Extract data from CSV file"""
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Successfully extracted {len(df)} records from {file_path}")
            return df
        except Exception as e:
            logger.error(f"Error extracting data from {file_path}: {str(e)}")
            raise

    def transform_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Transform the data into the required format"""
        try:
            # Convert date and time
            df['trans_date'] = pd.to_datetime(df['TRANS_DATE'])
            
            # Convert numeric columns
            numeric_columns = ['DISCOUNT_HEADER', 'TAX_HEADER', 'NET_SALES_HEADER_VALUES', 
                             'quantity', 'TRANS_TYPE', 'ID_KEY', 'DM_LOAD_DELTA_ID']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Handle NULL values in TENDER column
            df['TENDER'] = df['TENDER'].replace('NULL', None)

            # Convert to list of dictionaries with lowercase keys
            records = df.rename(columns=lambda x: x.lower()).to_dict('records')
            
            # Add processed flag for MongoDB tracking
            for record in records:
                record['processed'] = False
                record['trans_date'] = record['trans_date'].isoformat()
            
            logger.info(f"Successfully transformed {len(records)} records")
            return records
        except Exception as e:
            logger.error(f"Error transforming data: {str(e)}")
            raise

    async def load_to_mongodb(self, records: List[Dict[str, Any]]) -> int:
        """Load the transformed data into MongoDB"""
        try:
            # Ensure MongoDB is connected
            await mongodb.ensure_connected()
            
            loaded_count = 0
            failed_count = 0
            
            for record in records:
                try:
                    success = await mongodb.insert_raw_transaction(record)
                    if success:
                        loaded_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Error inserting record: {str(e)}")
                    failed_count += 1
            
            if failed_count > 0:
                logger.warning(f"Failed to load {failed_count} records")
            
            logger.info(f"Successfully loaded {loaded_count} records into MongoDB")
            return loaded_count
        except Exception as e:
            logger.error(f"Error loading data into MongoDB: {str(e)}")
            raise

    async def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process the entire ETL pipeline for a file"""
        try:
            # Extract
            df = self.extract_from_csv(file_path)
            
            # Transform
            records = self.transform_data(df)
            
            # Load to MongoDB
            loaded_count = await self.load_to_mongodb(records)
            
            if loaded_count == 0:
                raise Exception("No records were loaded into MongoDB")
            
            # Sync to SQLite
            sync_result = await self.sync_service.sync_transactions(batch_size=loaded_count)
            
            result = {
                "file": os.path.basename(file_path),
                "records_extracted": len(df),
                "records_transformed": len(records),
                "records_loaded_mongodb": loaded_count,
                "records_synced_sqlite": sync_result["synced"],
                "sync_errors": sync_result["errors"]
            }
            
            logger.info(f"ETL process completed successfully for {file_path}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"ETL process failed: {str(e)}")
            raise