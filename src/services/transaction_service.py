from src.repositories.transaction_repository import TransactionRepository
from src.models.pos_transaction import POSTransaction
from src.models.database_models import TransactionModel

class TransactionService:
    def __init__(self, repository: TransactionRepository):
        self.repository = repository

    async def save_transaction(self, transaction: POSTransaction):
        db_transaction = TransactionModel(
            store_code=transaction.store_code,
            store_display_name=transaction.store_display_name,
            trans_date=transaction.trans_date,
            trans_time=transaction.trans_time,
            trans_no=transaction.trans_no,
            till_no=transaction.till_no,
            discount_header=transaction.discount_header,
            tax_header=transaction.tax_header,
            net_sales_header_values=transaction.net_sales_header_values,
            quantity=transaction.quantity,
            trans_type=transaction.trans_type,
            id_key=transaction.id_key,
            tender=transaction.tender,
            dm_load_date=transaction.dm_load_date,
            dm_load_delta_id=transaction.dm_load_delta_id
        )
        return await self.repository.save_transaction(db_transaction) 