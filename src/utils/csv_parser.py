from typing import Dict, List, Tuple, Optional
import csv
from io import StringIO
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class POSDataParser:
    def __init__(self):
        # All fields from the CSV
        self.all_fields = [
            'STORE_CODE', 'STORE_DISPLAY_NAME', 'TRANS_DATE', 'TRANS_TIME',
            'TRANS_NO', 'TILL_NO', 'DISCOUNT_HEADER', 'TAX_HEADER',
            'NET_SALES_HEADER_VALUES', 'quantity', 'TRANS_TYPE', 'ID_KEY',
            'TENDER', 'DM_LOAD_DATE', 'DM_LOAD_DELTA_ID'
        ]
        
        # Required fields with their CSV names
        self.field_mappings = {
            'store_code': ['STORE_CODE'],
            'store_display_name': ['STORE_DISPLAY_NAME'],
            'trans_date': ['TRANS_DATE'],
            'trans_time': ['TRANS_TIME'],
            'trans_no': ['TRANS_NO'],
            'net_sales_header_values': ['NET_SALES_HEADER_VALUES'],
            'discount_header': ['DISCOUNT_HEADER'],
            'tax_header': ['TAX_HEADER'],
            'till_no': ['TILL_NO'],
            'quantity': ['quantity'],
            'trans_type': ['TRANS_TYPE'],
            'id_key': ['ID_KEY'],
            'tender': ['TENDER'],
            'dm_load_date': ['DM_LOAD_DATE'],
            'dm_load_delta_id': ['DM_LOAD_DELTA_ID']
        }
        
        self.required_fields = [
            'store_code', 'store_display_name', 'trans_date', 
            'trans_time', 'trans_no', 'net_sales_header_values',
            'discount_header', 'tax_header'
        ]
        
        self.numeric_fields = [
            'net_sales_header_values', 'discount_header', 'tax_header',
            'quantity', 'trans_type', 'id_key', 'dm_load_delta_id'
        ]
        
        # Update date formats to handle more variations
        self.date_formats = ['%m/%d/%y', '%m/%d/%Y', '%Y-%m-%d', '%d/%m/%y', '%d/%m/%Y']
        self.time_formats = ['%H:%M:%S', '%I:%M:%S', '%H:%M', '%I:%M']  # Add support for times without seconds

    def _map_column_names(self, fieldnames):
        """Map CSV column names to standard field names"""
        if not fieldnames:
            return {}
            
        column_mapping = {}
        fieldnames_lower = [f.lower().strip() for f in fieldnames]
        
        for standard_name, variations in self.field_mappings.items():
            for variation in variations:
                try:
                    idx = fieldnames_lower.index(variation.lower())
                    column_mapping[standard_name] = fieldnames[idx]
                    break
                except ValueError:
                    continue
                    
        return column_mapping

    def parse_csv_content(self, content: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse CSV content with validation and error tracking"""
        transactions = []
        errors = []
        
        try:
            # Remove any BOM if present
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # Ensure content is not empty
            if not content.strip():
                raise ValueError("Empty CSV file")
            
            # First detect the delimiter and header
            try:
                # Try to detect dialect from first few lines
                sample_lines = '\n'.join(content.split('\n')[:5])
                dialect = csv.Sniffer().sniff(sample_lines)
                has_header = csv.Sniffer().has_header(sample_lines)
            except Exception as e:
                logger.warning(f"Failed to detect CSV format: {str(e)}, using default")
                dialect = csv.excel
                has_header = True  # Assume headers by default
            
            # Read the CSV content
            csv_file = StringIO(content)
            reader = csv.reader(csv_file, dialect)
            
            # Read headers
            try:
                headers = next(reader)
                if not headers or not any(headers):  # Check if headers are empty
                    raise ValueError("CSV file has no valid headers")
                
                # Clean headers (remove BOM, whitespace, etc.)
                headers = [h.strip().replace('\ufeff', '') for h in headers]
                
                # Validate that we have at least some valid headers
                if not any(h for h in headers if h):
                    raise ValueError("All headers in CSV file are empty")
                
                # Map column names
                column_mapping = self._map_column_names(headers)
                missing_fields = [field for field in self.required_fields if field not in column_mapping]
                
                if missing_fields:
                    available_headers = ', '.join(f'"{h}"' for h in headers if h)
                    error_msg = (
                        f"Missing required columns: {missing_fields}. "
                        f"Available columns: [{available_headers}]. "
                        f"Please ensure your CSV file has all required columns: {self.required_fields}"
                    )
                    raise ValueError(error_msg)
                
            except StopIteration:
                raise ValueError("CSV file is empty or has no headers")
            
            # Process rows
            for row_num, row in enumerate(reader, start=1):
                try:
                    if not any(cell.strip() for cell in row):  # Skip empty rows
                        continue
                    
                    if len(row) != len(headers):
                        errors.append({
                            'row': row_num,
                            'error': f"Invalid column count. Expected {len(headers)}, got {len(row)}",
                            'data': dict(zip(headers[:len(row)], row))
                        })
                        continue
                    
                    # Convert row to dict using column mapping
                    row_dict = {}
                    for standard_name, csv_name in column_mapping.items():
                        try:
                            value = row[headers.index(csv_name)].strip()
                            row_dict[standard_name] = value
                        except (ValueError, IndexError) as e:
                            logger.error(f"Error mapping column {csv_name}: {str(e)}")
                            row_dict[standard_name] = ''
                    
                    cleaned_row = self.parse_line(row_dict, row_num)
                    if cleaned_row:
                        transactions.append(cleaned_row)
                except ValueError as e:
                    errors.append({
                        'row': row_num,
                        'error': str(e),
                        'data': dict(zip(headers, row))
                    })
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error parsing row {row_num}: {str(e)}")
                    errors.append({
                        'row': row_num,
                        'error': f"Unexpected error: {str(e)}",
                        'data': dict(zip(headers, row))
                    })
                    continue
            
            if not transactions and errors:
                logger.error("No valid transactions found in CSV")
            elif transactions:
                logger.info(f"Successfully parsed {len(transactions)} transactions with {len(errors)} errors")
            
            return transactions, errors
            
        except ValueError as e:
            logger.error(f"CSV parsing error: {str(e)}")
            errors.append({
                'row': 0,
                'error': f"CSV format error: {str(e)}"
            })
            return [], errors
        except Exception as e:
            logger.error(f"Unexpected error parsing CSV: {str(e)}")
            errors.append({
                'row': 0,
                'error': f"Unexpected error: {str(e)}"
            })
            return [], errors

    def parse_line(self, row: Dict, row_num: int) -> Optional[Dict]:
        """Parse and validate a single line of CSV data"""
        try:
            # Check for missing required fields
            missing_fields = []
            for field in self.required_fields:
                if not row.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Clean and validate the row
            cleaned = {}
            
            # Validate and parse date
            trans_date = None
            date_str = row['trans_date'].strip()
            for date_format in self.date_formats:
                try:
                    trans_date = datetime.strptime(date_str, date_format)
                    break
                except ValueError:
                    continue
            
            if trans_date is None:
                raise ValueError(f"Invalid date format for trans_date: {date_str}. Expected formats: MM/DD/YY, MM/DD/YYYY, YYYY-MM-DD")
            cleaned['trans_date'] = trans_date.date().isoformat()
            
            # Validate and parse time
            trans_time = None
            time_str = row['trans_time'].strip()
            # Add leading zero for single-digit hours
            if ':' in time_str and len(time_str.split(':')[0]) == 1:
                time_str = '0' + time_str
            
            for time_format in self.time_formats:
                try:
                    trans_time = datetime.strptime(time_str, time_format)
                    break
                except ValueError:
                    continue
            
            if trans_time is None:
                raise ValueError(f"Invalid time format for trans_time: {time_str}. Expected formats: HH:MM:SS, HH:MM")
            cleaned['trans_time'] = trans_time.time().isoformat()
            
            # Validate and convert numeric fields
            for field in self.numeric_fields:
                try:
                    value = row.get(field, '0').strip()
                    # Handle empty or invalid values
                    if not value or value.lower() == 'null':
                        cleaned[field] = 0
                    else:
                        # Remove currency symbols, commas, and handle negative values
                        value = value.replace('$', '').replace(',', '').strip()
                        if field in ['net_sales_header_values', 'discount_header', 'tax_header']:
                            cleaned[field] = float(value)  # Keep as float for monetary values
                        else:
                            cleaned[field] = int(float(value))  # Convert to integer for other fields
                except (ValueError, AttributeError):
                    if field in self.required_fields:
                        raise ValueError(f"Invalid numeric value in {field}: {row.get(field, 'missing')}")
                    else:
                        cleaned[field] = 0  # Default for non-required numeric fields
            
            # Validate store code format (allow any 4 letter prefix followed by 4 digits)
            store_code = row['store_code'].strip()
            if not (len(store_code) == 8 and store_code[:4].isalpha() and store_code[4:].isdigit()):
                raise ValueError(f"Invalid store code format: {store_code}. Expected format: 4 letters followed by 4 digits")
            cleaned['store_code'] = store_code
            
            # Clean and validate store display name
            store_name = row['store_display_name'].strip()
            if not store_name:
                raise ValueError("Empty store display name")
            cleaned['store_display_name'] = store_name
            
            # Validate transaction number (more flexible format)
            trans_no = row['trans_no'].strip()
            if not trans_no:
                raise ValueError("Empty transaction number")
            # Allow any format that has a hyphen and numbers
            if not ('-' in trans_no and any(c.isdigit() for c in trans_no)):
                raise ValueError(f"Invalid transaction number format: {trans_no}. Expected format: prefix-number")
            cleaned['trans_no'] = trans_no
            
            # Copy string fields
            cleaned['till_no'] = row.get('till_no', '').strip()
            cleaned['tender'] = None if row.get('tender', '').strip().upper() == 'NULL' else row.get('tender', '').strip()
            cleaned['dm_load_date'] = row.get('dm_load_date', '').strip()
            
            return cleaned
            
        except ValueError as e:
            raise ValueError(f"Error parsing line: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error parsing line {row_num}: {str(e)}")
            raise ValueError(f"Unexpected error: {str(e)}")

    def validate_date_format(self, date_str: str) -> bool:
        """Validate date string format"""
        for date_format in self.date_formats:
            try:
                datetime.strptime(date_str, date_format)
                return True
            except ValueError:
                continue
        return False

    def validate_time_format(self, time_str: str) -> bool:
        """Validate time string format"""
        # Add leading zero for single-digit hours
        if len(time_str.split(':')[0]) == 1:
            time_str = '0' + time_str
            
        for time_format in self.time_formats:
            try:
                datetime.strptime(time_str, time_format)
                return True
            except ValueError:
                continue
        return False