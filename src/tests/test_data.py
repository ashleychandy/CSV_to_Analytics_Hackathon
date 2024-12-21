import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_test_data(num_records=100, output_file=None):
    """Generate test data for POS transactions."""
    
    # Define store data
    stores = [
        ("S001", "Store One"),
        ("S002", "Store Two"),
        ("S003", "Store Three")
    ]
    
    # Define tender types
    tenders = ["CASH", "CREDIT", "DEBIT", "GIFT_CARD"]
    
    # Generate random dates within the last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    dates = pd.date_range(start=start_date, end=end_date, periods=num_records)
    
    # Generate random data
    data = {
        "store_code": [store[0] for store in np.random.choice(stores, num_records)],
        "store_display_name": [store[1] for store in np.random.choice(stores, num_records)],
        "trans_date": dates.date,
        "trans_time": [f"{np.random.randint(0, 24):02d}:{np.random.randint(0, 60):02d}:00" for _ in range(num_records)],
        "trans_no": [f"T{i+1:06d}" for i in range(num_records)],
        "till_no": [f"{np.random.randint(1, 6)}" for _ in range(num_records)],
        "discount_header": np.random.uniform(0, 50, num_records).round(2),
        "tax_header": np.random.uniform(5, 20, num_records).round(2),
        "net_sales_header_values": np.random.uniform(10, 1000, num_records).round(2),
        "quantity": np.random.randint(1, 10, num_records),
        "trans_type": ["SALE" for _ in range(num_records)],
        "tender": np.random.choice(tenders, num_records)
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    if output_file:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        # Save to CSV
        df.to_csv(output_file, index=False)
        return output_file
    
    return df

def generate_test_files(num_files=3, records_per_file=100, output_dir="data/test"):
    """Generate multiple test files."""
    files = []
    for i in range(num_files):
        filename = os.path.join(output_dir, f"test_data_{i+1}.csv")
        files.append(generate_test_data(records_per_file, filename))
    return files

if __name__ == "__main__":
    # Generate test files
    test_files = generate_test_files()
    print(f"Generated test files: {test_files}") 