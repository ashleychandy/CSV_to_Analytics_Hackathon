from typing import Dict, List
from datetime import datetime
import csv
from io import StringIO

class POSDataParser:
    def __init__(self):
        self.field_names = [
            'store_code', 'store_display_name', 'trans_date', 'trans_time',
            'trans_no', 'till_no', 'discount_header', 'tax_header',
            'net_sales_header_values', 'quantity', 'trans_type', 'id_key',
            'tender', 'dm_load_date', 'dm_load_delta_id'
        ]

    def parse_line(self, line: str, delimiter: str = None) -> Dict:
        try:
            # Detect delimiter if not provided
            if delimiter is None:
                if '|' in line:
                    delimiter = '|'
                else:
                    delimiter = ','
            
            # Parse CSV line
            reader = csv.DictReader(StringIO(line), fieldnames=self.field_names, delimiter=delimiter)
            data = next(reader)
            
            # Validate store code
            store_code = data['store_code'].strip()
            if not (store_code.startswith('BIAL') or store_code.startswith('TFSB')):
                raise ValueError(f"Invalid store code: {store_code}")
            
            # Parse date
            try:
                trans_date = datetime.strptime(data['trans_date'], '%m/%d/%y')
            except ValueError:
                raise ValueError(f"Invalid date format: {data['trans_date']}, expected MM/DD/YY")
            
            return {
                'store_code': store_code,
                'store_display_name': data['store_display_name'].strip(),
                'trans_date': trans_date.date().isoformat(),
                'trans_time': data['trans_time'].strip(),
                'trans_no': data['trans_no'].strip(),
                'till_no': data['till_no'].strip(),
                'discount_header': float(data['discount_header'] or 0),
                'tax_header': float(data['tax_header'] or 0),
                'net_sales_header_values': float(data['net_sales_header_values'] or 0),
                'quantity': int(data['quantity'] or 0),
                'trans_type': int(data['trans_type'] or 0),
                'id_key': int(data['id_key'] or 0),
                'tender': None if data['tender'] == 'NULL' else data['tender'].strip(),
                'dm_load_date': data['dm_load_date'].strip(),
                'dm_load_delta_id': int(data['dm_load_delta_id'] or 0)
            }
        except Exception as e:
            raise ValueError(f"Error parsing line: {str(e)}")

    def parse_csv_content(self, content: str) -> List[Dict]:
        """Parse entire CSV content including header"""
        lines = content.splitlines()
        if not lines:
            raise ValueError("Empty file")
            
        # Detect delimiter
        first_line = lines[0]
        delimiter = '|' if '|' in first_line else ','
        
        # Skip header if present
        if any(header in first_line.upper() for header in ['STORE_CODE', 'TRANS_DATE']):
            lines = lines[1:]
            
        transactions = []
        errors = []
        
        for i, line in enumerate(lines, 1):
            if line.strip():
                try:
                    transaction = self.parse_line(line, delimiter)
                    transactions.append(transaction)
                except Exception as e:
                    errors.append(f"Line {i}: {str(e)}")
                    
        return transactions, errors

    def _parse_float(self, value: str) -> float:
        try:
            return float(value.strip())
        except ValueError:
            return 0.0