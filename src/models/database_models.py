from sqlalchemy import Column, String, DateTime, Float, Integer, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TransactionModel(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    store_code = Column(String(50), nullable=False)
    store_display_name = Column(String(100))
    trans_date = Column(DateTime, nullable=False)
    trans_time = Column(String(20))
    trans_no = Column(String(50), unique=True, nullable=False)
    till_no = Column(String(20))
    discount_header = Column(Float, default=0.0)
    tax_header = Column(Float, default=0.0)
    net_sales_header_values = Column(Float, default=0.0)
    quantity = Column(Integer, default=0)
    trans_type = Column(Integer, default=0)
    id_key = Column(Integer)
    dm_load_date = Column(String(50))
    dm_load_delta_id = Column(Integer)

    __table_args__ = (
        UniqueConstraint('trans_no', name='uix_trans_no'),
    ) 