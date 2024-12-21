import pytest
from src.services.data_processor import POSDataProcessor
from src.services.etl_service import ETLService

async def test_process_transaction():
    processor = POSDataProcessor()
    
    # Test data matching the format from csv_parser.py
    test_data = "BIAL0128|TFS BLR Lounge-East Pier|9/13/24|0:08:28|00IDB-1000021978|POS2|0|0|910|1|0|1398249674|NULL|38:00.6|6883"
    
    try:
        transaction = await processor.process_transaction(test_data)
        assert transaction.store_code == "BIAL0128"
        assert transaction.trans_no == "00IDB-1000021978"
        assert transaction.net_sales_header_values == 910.0
        print("✅ Transaction processing test passed")
        return True
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False 