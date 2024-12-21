from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class POSTransaction(Base):
    __tablename__ = 'pos_transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_code = Column(String(50), nullable=False)
    store_display_name = Column(String(100), nullable=False)
    trans_date = Column(DateTime, nullable=False)
    trans_time = Column(String(20), nullable=False)
    trans_no = Column(String(50), nullable=False)
    till_no = Column(String(20), nullable=False)
    discount_header = Column(Float, default=0)
    tax_header = Column(Float, default=0)
    net_sales_header_values = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    trans_type = Column(Integer, default=0)
    id_key = Column(BigInteger, nullable=False, unique=True)
    tender = Column(String(50))
    dm_load_date = Column(String(50))
    dm_load_delta_id = Column(Integer) 