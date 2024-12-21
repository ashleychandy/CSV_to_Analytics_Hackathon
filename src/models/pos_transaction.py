from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class POSTransaction:
    store_code: str
    store_display_name: str
    trans_date: datetime
    trans_time: str
    trans_no: str
    till_no: str
    discount_header: float
    tax_header: float
    net_sales_header_values: float
    quantity: int
    trans_type: int
    id_key: int
    tender: Optional[str]
    dm_load_date: str
    dm_load_delta_id: int 