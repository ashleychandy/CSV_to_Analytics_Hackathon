from sqlalchemy.orm import Session
from src.models.database_models import TransactionModel

class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    async def save_transaction(self, transaction: TransactionModel):
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction 