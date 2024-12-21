from typing import Dict
from datetime import datetime

class POSDataParser:
    def parse_line(self, line: str) -> Dict:
        try:
            fields = line.strip().split('|')
            if len(fields) != 15:
                raise ValueError(f"Expected 15 fields, got {len(fields)}")
            
            # Try multiple date formats
            date_formats = ['%m/%d/%y', '%Y-%m-%d', '%d/%m/%Y']
            trans_date = None
            
            for fmt in date_formats:
                try:
                    trans_date = datetime.strptime(fields[2], fmt)
                    break
                except ValueError:
                    continue
                    
            if not trans_date:
                raise ValueError(f"Unable to parse date: {fields[2]}")
            
            return {
                'store_code': fields[0].strip(),
                'store_display_name': fields[1].strip(),
                'trans_date': trans_date.date().isoformat(),
                'trans_time': fields[3].strip(),
                'trans_no': fields[4].strip(),
                'till_no': fields[5].strip(),
                'discount_header': self._parse_float(fields[6]),
                'tax_header': self._parse_float(fields[7]),
                'net_sales_header_values': self._parse_float(fields[8]),
                'quantity': int(fields[9]),
                'trans_type': int(fields[10]),
                'id_key': int(fields[11]),
                'tender': None if fields[12] == 'NULL' else fields[12].strip(),
                'dm_load_date': fields[13].strip(),
                'dm_load_delta_id': int(fields[14])
            }
        except Exception as e:
            raise ValueError(f"Error parsing line: {str(e)}")

    def _parse_float(self, value: str) -> float:
        try:
            return float(value.strip())
        except ValueError:
            return 0.0