import pandas as pd
import logging
from datetime import datetime
import uuid
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from src.models.pos_transaction import POSTransaction
from src.config.settings import settings

logger = logging.getLogger(__name__)

class ETLService:
    """Service for ETL operations."""

    def __init__(self, db: Session):
        """Initialize ETL service."""
        self.db = db
        self.required_columns = {
            'store_code',
            'store_display_name',
            'trans_date',
            'trans_time',
            'trans_no',
            'till_no',
            'net_sales_header_values',
            'quantity'
        }

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate DataFrame has required columns."""
        # Convert column names to lowercase for case-insensitive comparison
        df_columns = {col.lower() for col in df.columns}
        return self.required_columns.issubset(df_columns)

    def clean_numeric(self, value: Any) -> float:
        """Clean numeric values."""
        if pd.isna(value):
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    async def process_file(self, file_path: str = None, user_id: int = None) -> dict:
        """Process CSV file and store in database."""
        try:
            if file_path:
                # Read and validate CSV
                df = pd.read_csv(file_path)
                if not self.validate_data(df):
                    raise ValueError(f"Missing required columns. Required: {self.required_columns}")

                # Convert column names to match database fields
                df.columns = [col.lower() for col in df.columns]

                # Add user_id to each record
                if user_id:
                    df['user_id'] = user_id

                # Convert date and time fields - try multiple formats
                try:
                    # First try %m/%d/%y format
                    df['trans_date'] = pd.to_datetime(df['trans_date'], format='%m/%d/%y')
                except ValueError:
                    try:
                        # Then try %Y-%m-%d format
                        df['trans_date'] = pd.to_datetime(df['trans_date'], format='%Y-%m-%d')
                    except ValueError:
                        # If both fail, let pandas infer the format
                        df['trans_date'] = pd.to_datetime(df['trans_date'])

                df['dm_load_date'] = datetime.now()
                df['dm_load_delta_id'] = str(uuid.uuid4())

                # Clean numeric fields
                df['net_sales_header_values'] = df['net_sales_header_values'].apply(self.clean_numeric)
                df['discount_header'] = df.get('discount_header', 0.0).apply(self.clean_numeric)
                df['tax_header'] = df.get('tax_header', 0.0).apply(self.clean_numeric)
                df['quantity'] = df['quantity'].fillna(0).astype(int)

                # Set default values for optional fields
                df['trans_type'] = df.get('trans_type', 'SALE')
                df['tender'] = df.get('tender', 'CASH')

                # Convert to records
                records = df.to_dict('records')

                # Insert in batches
                batch_size = settings.batch_size
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    self.db.bulk_insert_mappings(POSTransaction, batch)
                    self.db.commit()

                return {
                    "status": "success",
                    "records_processed": len(records),
                    "message": f"Successfully processed {len(records)} records"
                }

            return {
                "status": "success",
                "records_synced": 0,
                "message": "Successfully synced 0 records"
            }

        except Exception as e:
            self.db.rollback()
            raise e

    async def _process_batch(self, df: pd.DataFrame, user_id: int) -> int:
        """Process a batch of records."""
        try:
            # Convert column names to lowercase
            df.columns = df.columns.str.lower()
            
            # Validate data
            self.validate_data(df)
            
            records = []
            for _, row in df.iterrows():
                try:
                    # Convert date string to datetime
                    trans_date = pd.to_datetime(row.get('trans_date'), format='%m/%d/%y').date() if pd.notna(row.get('trans_date')) else None
                    if not trans_date:
                        logger.warning(f"Skipping record with invalid date: {row.get('trans_date')}")
                        continue

                    # Ensure user_id is set for each record
                    if not user_id:
                        logger.warning("No user_id provided for record")
                        continue

                    transaction = POSTransaction(
                        user_id=user_id,  # Explicitly set user_id for each record
                        store_code=str(row.get('store_code', '')),
                        store_display_name=str(row.get('store_display_name', '')),
                        trans_date=trans_date,
                        trans_time=str(row.get('trans_time', '')),
                        trans_no=str(row.get('trans_no', '')),
                        till_no=str(row.get('till_no', '')),
                        discount_header=self.clean_numeric(row.get('discount_header', 0)),
                        tax_header=self.clean_numeric(row.get('tax_header', 0)),
                        net_sales_header_values=self.clean_numeric(row.get('net_sales_header_values', 0)),
                        quantity=int(self.clean_numeric(row.get('quantity', 0))),
                        trans_type=str(row.get('trans_type', 'SALE')),
                        tender=str(row.get('tender', 'CASH')),
                        dm_load_date=datetime.now(),
                        dm_load_delta_id=1
                    )
                    records.append(transaction)

                    if len(records) >= settings.batch_size:
                        self.db.bulk_save_objects(records)
                        self.db.commit()
                        records = []

                except Exception as e:
                    logger.error(f"Error processing record: {str(e)}")
                    continue

            if records:
                self.db.bulk_save_objects(records)
                self.db.commit()

            return len(df)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing batch: {str(e)}")
            raise

    async def _sync_transactions(self) -> int:
        """Sync transactions from source to destination."""
        try:
            # Implement your sync logic here
            # For example, syncing from a staging table or external source
            return 0
        except Exception as e:
            logger.error(f"Error syncing transactions: {str(e)}")
            raise

    def clean_string(self, value: Any) -> str:
        """Clean and convert string values."""
        if pd.isna(value):
            return ''
        return str(value).strip()

    def extract_from_csv(self, file_path: str) -> pd.DataFrame:
        """Extract data from CSV file"""
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Successfully extracted {len(df)} records from {file_path}")
            return df
        except Exception as e:
            logger.error(f"Error extracting data from {file_path}: {str(e)}")
            raise

    def transform_data(self, df: pd.DataFrame, user_id: int = None) -> List[Dict[str, Any]]:
        """Transform the data into the required format"""
        try:
            # Convert date and time
            df['trans_date'] = pd.to_datetime(df['TRANS_DATE'], format='%m/%d/%y')
            
            # Convert numeric columns
            numeric_columns = ['DISCOUNT_HEADER', 'TAX_HEADER', 'NET_SALES_HEADER_VALUES', 
                             'quantity', 'TRANS_TYPE', 'ID_KEY', 'DM_LOAD_DELTA_ID']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Handle NULL values in TENDER column
            df['TENDER'] = df['TENDER'].replace('NULL', None)

            # Convert to list of dictionaries with lowercase keys
            records = df.rename(columns=lambda x: x.lower()).to_dict('records')
            
            # Add processed flag and user_id for tracking
            for record in records:
                record['processed'] = False
                record['trans_date'] = record['trans_date'].isoformat()
                if user_id:
                    record['user_id'] = user_id
            
            logger.info(f"Successfully transformed {len(records)} records for user {user_id}")
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