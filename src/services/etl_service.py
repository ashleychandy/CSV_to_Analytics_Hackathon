import pandas as pd
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from models.pos_transaction import POSTransaction
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)

class ETLService:
    def __init__(self, db: Session):
        self.db = db

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
            
            logger.info(f"Successfully transformed {len(records)} records")
            return records
        except Exception as e:
            logger.error(f"Error transforming data: {str(e)}")
            raise

    def load_data(self, records: List[Dict[str, Any]]) -> None:
        """Load the transformed data into the database with upsert logic"""
        try:
            for record in records:
                # Check if record with this id_key exists
                existing = self.db.query(POSTransaction).filter_by(id_key=record['id_key']).first()
                
                if existing:
                    # Update existing record
                    for key, value in record.items():
                        setattr(existing, key, value)
                else:
                    # Create new record
                    pos_transaction = POSTransaction(
                        store_code=record['store_code'],
                        store_display_name=record['store_display_name'],
                        trans_date=record['trans_date'],
                        trans_time=record['trans_time'],
                        trans_no=record['trans_no'],
                        till_no=record['till_no'],
                        discount_header=record['discount_header'],
                        tax_header=record['tax_header'],
                        net_sales_header_values=record['net_sales_header_values'],
                        quantity=record['quantity'],
                        trans_type=record['trans_type'],
                        id_key=record['id_key'],
                        tender=record.get('tender'),
                        dm_load_date=record['dm_load_date'],
                        dm_load_delta_id=record['dm_load_delta_id']
                    )
                    self.db.add(pos_transaction)
            
            self.db.commit()
            logger.info(f"Successfully loaded {len(records)} records into database")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error loading data into database: {str(e)}")
            raise

    def process_file(self, file_path: str) -> None:
        """Process the entire ETL pipeline for a file"""
        try:
            df = self.extract_from_csv(file_path)
            records = self.transform_data(df)
            self.load_data(records)
            logger.info(f"ETL process completed successfully for {file_path}")
        except Exception as e:
            logger.error(f"ETL process failed: {str(e)}")
            raise