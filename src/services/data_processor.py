from typing import Dict, List
import logging
from datetime import datetime
from src.models.pos_transaction import POSTransaction
from src.utils.csv_parser import POSDataParser
from src.services.interfaces.processor_interface import TransactionProcessorInterface
from src.services.etl_service import ETLService
from src.utils.status_monitor import ProcessingMonitor

class POSDataProcessor(TransactionProcessorInterface):
    def __init__(self):
        self.logger = logging.getLogger("pos_revenue")
        self.parser = POSDataParser()
        self.monitor = ProcessingMonitor()
        self.etl_service = ETLService(self.monitor)

    async def process_transaction(self, raw_data: str) -> POSTransaction:
        try:
            parsed_data = self.parser.parse_line(raw_data)
            
            cleaned_data = self.etl_service.clean_transaction(parsed_data)
            
            transaction = POSTransaction(**cleaned_data)
            
            self.logger.info(f"Processed transaction: {transaction.trans_no}")
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error processing transaction: {str(e)}")
            raise 