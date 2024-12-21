from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.db.base import Base

class POSTransaction(Base):
    """POS Transaction model."""
    __tablename__ = "pos_transactions"

    id = Column(Integer, primary_key=True, index=True)
    store_code = Column(String, index=True)
    store_display_name = Column(String)
    trans_date = Column(DateTime)
    trans_time = Column(String)
    trans_no = Column(String, index=True)
    till_no = Column(String)
    net_sales_header_values = Column(Float)
    quantity = Column(Integer)
    trans_type = Column(String)
    tender = Column(String)
    discount_header = Column(Float)
    tax_header = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"))
    dm_load_date = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", backref="transactions")

    def __repr__(self):
        return f"<POSTransaction {self.trans_no}>"