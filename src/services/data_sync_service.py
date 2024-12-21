import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.pos_transaction import POSTransaction
from src.db.database import mongodb
from typing import List, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

class DataSyncService:
    def __init__(self, db: Session):
        self.db = db

    def _create_pos_transaction(self, record: Dict[str, Any]) -> POSTransaction:
        """Create a POSTransaction object from a MongoDB record"""
        try:
            return POSTransaction(
                store_code=record['store_code'],
                store_display_name=record['store_display_name'],
                trans_date=datetime.fromisoformat(record['trans_date']),
                trans_time=record['trans_time'],
                trans_no=record['trans_no'],
                till_no=record['till_no'],
                discount_header=float(record['discount_header'] or 0),
                tax_header=float(record['tax_header'] or 0),
                net_sales_header_values=float(record['net_sales_header_values'] or 0),
                quantity=int(record['quantity'] or 0),
                trans_type=int(record['trans_type'] or 0),
                id_key=int(record['id_key']),
                tender=record.get('tender'),
                dm_load_date=record['dm_load_date'],
                dm_load_delta_id=int(record['dm_load_delta_id'] or 0)
            )
        except Exception as e:
            logger.error(f"Error creating POSTransaction: {str(e)}, Record: {record}")
            raise

    async def sync_transactions(self, batch_size: int = 100) -> Dict[str, int]:
        """Sync unprocessed transactions from MongoDB to SQLite"""
        try:
            # Get unprocessed transactions from MongoDB
            transactions = await mongodb.get_unprocessed_transactions(batch_size)
            if not transactions:
                logger.info("No unprocessed transactions found")
                return {"synced": 0, "errors": 0}

            transaction_ids = []
            error_count = 0
            synced_count = 0

            # Process each transaction
            for record in transactions:
                try:
                    # Check if record already exists in SQLite
                    existing = self.db.query(POSTransaction).filter_by(
                        id_key=record['id_key']
                    ).first()

                    if existing:
                        # Update existing record
                        for key, value in record.items():
                            if key not in ['_id', 'processed']:
                                if key == 'trans_date':
                                    value = datetime.fromisoformat(value)
                                elif key in ['discount_header', 'tax_header', 'net_sales_header_values']:
                                    value = float(value or 0)
                                elif key in ['quantity', 'trans_type', 'dm_load_delta_id']:
                                    value = int(value or 0)
                                setattr(existing, key, value)
                    else:
                        # Create new record
                        pos_transaction = self._create_pos_transaction(record)
                        self.db.add(pos_transaction)

                    transaction_ids.append(record['_id'])
                    synced_count += 1
                except Exception as e:
                    logger.error(f"Error processing transaction {record.get('id_key')}: {str(e)}")
                    error_count += 1
                    continue

            # Commit SQLite changes
            if transaction_ids:
                try:
                    self.db.commit()
                    # Mark transactions as processed in MongoDB
                    processed_count = await mongodb.mark_as_processed(transaction_ids)
                    if processed_count != len(transaction_ids):
                        logger.warning(f"Only {processed_count} of {len(transaction_ids)} transactions were marked as processed")
                    return {"synced": synced_count, "errors": error_count}
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Error committing transactions: {str(e)}")
                    return {"synced": 0, "errors": len(transactions)}

            return {"synced": synced_count, "errors": error_count}

        except Exception as e:
            logger.error(f"Error syncing transactions: {str(e)}")
            return {"synced": 0, "errors": batch_size}

class AsyncDataSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_transactions(self, batch_size: int = 100) -> Dict[str, Any]:
        """Sync transactions from MongoDB to SQLite (async version)"""
        try:
            # Get unprocessed transactions from MongoDB
            transactions = await mongodb.get_unprocessed_transactions(batch_size)
            
            if not transactions:
                logger.info("No new transactions to sync")
                return {"synced": 0, "errors": 0}

            processed_ids = []
            error_count = 0

            # Process each transaction
            for transaction in transactions:
                try:
                    # Transform MongoDB document to SQLite record
                    pos_transaction = POSTransaction(
                        store_code=transaction.get('store_code'),
                        store_display_name=transaction.get('store_display_name'),
                        trans_date=datetime.fromisoformat(transaction.get('trans_date')),
                        trans_time=transaction.get('trans_time'),
                        trans_no=transaction.get('trans_no'),
                        till_no=transaction.get('till_no'),
                        discount_header=float(transaction.get('discount_header', 0)),
                        tax_header=float(transaction.get('tax_header', 0)),
                        net_sales_header_values=float(transaction.get('net_sales_header_values', 0)),
                        quantity=int(transaction.get('quantity', 0)),
                        trans_type=int(transaction.get('trans_type', 0)),
                        id_key=int(transaction.get('id_key')),
                        tender=transaction.get('tender'),
                        dm_load_date=transaction.get('dm_load_date'),
                        dm_load_delta_id=int(transaction.get('dm_load_delta_id', 0))
                    )
                    
                    # Add to SQLite
                    self.db.add(pos_transaction)
                    processed_ids.append(transaction['_id'])
                except Exception as e:
                    logger.error(f"Error processing transaction {transaction.get('_id')}: {str(e)}")
                    error_count += 1

            if processed_ids:
                # Commit SQLite changes
                await self.db.commit()
                
                # Mark transactions as processed in MongoDB
                processed_count = await mongodb.mark_as_processed(processed_ids)
                
                logger.info(f"Successfully synced {len(processed_ids)} transactions")
            
            return {
                "synced": len(processed_ids),
                "errors": error_count
            }

        except Exception as e:
            logger.error(f"Error in sync_transactions: {str(e)}")
            await self.db.rollback()
            raise

async def background_sync(interval_seconds: int = 60):
    """Background task to sync data periodically"""
    while True:
        try:
            async with AsyncSession() as session:
                sync_service = AsyncDataSyncService(session)
                result = await sync_service.sync_transactions()
                logger.info(f"Background sync completed: {result}")
        except Exception as e:
            logger.error(f"Error in background sync: {str(e)}")
        finally:
            await asyncio.sleep(interval_seconds) 