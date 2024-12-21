from typing import List, Dict
import pandas as pd
from src.db.database import mongodb
from sqlalchemy.orm import Session
from src.models.database_models import TransactionModel
from src.utils.status_monitor import ProcessingMonitor
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import select

class ETLService:
    def __init__(self, monitor: ProcessingMonitor):
        self.monitor = monitor
        self.vendor_transformers = {
            'BIAL': self._transform_bial_data,
            'TFSB': self._transform_tfs_data,
        }

    async def extract_from_mongodb(self) -> List[dict]:
        """Extract raw transactions from MongoDB"""
        self.monitor.update_status("Extracting data from MongoDB...")
        collection = mongodb.db.transactions
        return await collection.find({}).to_list(length=None)

    async def transform_data(self, raw_data: List[dict]) -> pd.DataFrame:
        """Transform and clean the data"""
        self.monitor.update_status("Transforming data...")
        try:
            if not raw_data:
                raise ValueError("No data to transform")
            
            df = pd.DataFrame(raw_data)
            required_columns = [
                'store_code', 'store_display_name', 'trans_date', 
                'trans_time', 'trans_no', 'net_sales_header_values'
            ]
            
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Convert date fields
            df['trans_date'] = pd.to_datetime(df['trans_date'])
            df['timestamp'] = pd.to_datetime(
                df['trans_date'].dt.strftime('%Y-%m-%d') + ' ' + df['trans_time']
            )
            
            # Convert numeric fields
            numeric_fields = ['discount_header', 'tax_header', 'net_sales_header_values']
            for field in numeric_fields:
                df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0.0)
            
            # Extract source system
            df['source_system'] = df['store_code'].str[:4]
            
            return df
            
        except Exception as e:
            self.monitor.update_status(f"Transform error: {str(e)}")
            raise ValueError(f"Transform error: {str(e)}")

    def _transform_bial_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform BIAL specific data"""
        # Add BIAL specific transformations
        df['store_region'] = 'BLR'
        df['terminal_type'] = df['till_no'].str.contains('POS').map({True: 'POS', False: 'KIOSK'})
        return df

    def _transform_tfs_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform TFS specific data"""
        # Add TFS specific transformations
        df['store_region'] = df['store_display_name'].str.extract(r'([A-Z]{3})\s+Lounge')
        df['is_duty_free'] = True
        return df

    async def load_to_sql(self, df: pd.DataFrame, db: Session):
        """Load transformed data into SQL database with upsert logic"""
        self.monitor.update_status("Loading data to SQL database...")
        
        batch_size = 1000
        total_rows = len(df)
        processed = 0
        
        try:
            for start in range(0, total_rows, batch_size):
                end = min(start + batch_size, total_rows)
                batch = df.iloc[start:end]
                
                # Convert batch to list of dictionaries
                records = batch.to_dict('records')
                
                # Upsert each record
                for record in records:
                    stmt = insert(TransactionModel).values(record)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['trans_no'],
                        set_=record
                    )
                    db.execute(stmt)
                
                processed += len(batch)
                self.monitor.update_status(f"Loaded {processed}/{total_rows} records...")
                db.commit()
                
        except Exception as e:
            db.rollback()
            raise Exception(f"Error loading data to SQL: {str(e)}")

    def clean_transaction(self, data: Dict) -> Dict:
        """Clean individual transaction data"""
        vendor_code = data['store_code'][:4]
        
        cleaned = {
            **data,
            'net_sales_header_values': float(data['net_sales_header_values']),
            'discount_header': float(data['discount_header']),
            'tax_header': float(data['tax_header']),
        }
        
        if vendor_code in self.vendor_transformers:
            cleaned = self.vendor_transformers[vendor_code](pd.DataFrame([cleaned])).iloc[0].to_dict()
        
        return cleaned