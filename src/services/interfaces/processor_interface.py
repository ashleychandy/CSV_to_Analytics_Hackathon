from abc import ABC, abstractmethod
from src.models.pos_transaction import POSTransaction

class TransactionProcessorInterface(ABC):
    @abstractmethod
    async def process_transaction(self, raw_data: str) -> POSTransaction:
        pass 