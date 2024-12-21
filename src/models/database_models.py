from sqlalchemy import Column, Integer, String, Float, DateTime
from src.db.database import Base

class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    store_code = Column(String)
    store_display_name = Column(String)
    trans_date = Column(DateTime)
    trans_time = Column(String)
    trans_no = Column(String, unique=True, index=True)
    till_no = Column(String)
    discount_header = Column(Float)
    tax_header = Column(Float)
    net_sales_header_values = Column(Float)
    quantity = Column(Integer)
    trans_type = Column(Integer)
    id_key = Column(Integer)
    tender = Column(String, nullable=True)
    dm_load_date = Column(String)
    dm_load_delta_id = Column(Integer) 