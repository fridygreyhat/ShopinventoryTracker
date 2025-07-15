
import io
import csv
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CSVImportService:
    """Service class for handling CSV imports with validation and error handling"""
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    REQUIRED_HEADERS = ['name']
    OPTIONAL_HEADERS = [
        'sku', 'description', 'category', 'quantity', 'buying_price',
        'selling_price_retail', 'selling_price_wholesale', 'sales_type'
    ]
    VALID_SALES_TYPES = ['retail', 'wholesale', 'both']
    
    def __init__(self, db_session, item_model, user_id=None):
        self.db = db_session
        self.Item = item_model
        self.user_id = user_id
        
    def validate_file(self, file) -> Dict[str, Any]:
        """Validate uploaded file before processing"""
        if not file or file.filename == '':
            return {"error": "No file selected"}
            
        if not file.filename.lower().endswith('.csv'):
            return {"error": "Only CSV files are supported"}
            
        # Check file size
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if size > self.MAX_FILE_SIZE:
            return {"error": "File too large. Maximum size is 5MB"}
            
        return {"valid": True}
    
    def read_csv_content(self, file) -> Tuple[Optional[csv.DictReader], Optional[str]]:
        """Read and decode CSV file with proper encoding handling"""
        try:
            # Try UTF-8 first
            content = file.stream.read().decode("UTF-8")
        except UnicodeDecodeError:
            try:
                file.stream.seek(0)
                content = file.stream.read().decode("ISO-8859-1")
            except UnicodeDecodeError:
                return None, "Unable to decode file. Please ensure it's a valid CSV file with UTF-8 or ISO-8859-1 encoding."
        
        stream = io.StringIO(content, newline=None)
        
        # Check if file has data
        first_line = stream.readline()
        if not first_line.strip():
            return None, "CSV file appears to be empty"
        
        # Reset stream and create CSV reader
        stream.seek(0)
        csv_reader = csv.DictReader(stream)
        
        return csv_reader, None
    
    def validate_headers(self, csv_reader: csv.DictReader) -> Optional[str]:
        """Validate CSV headers"""
        if not csv_reader.fieldnames:
            return "CSV file has no headers"
        
        missing_headers = [header for header in self.REQUIRED_HEADERS 
                          if header not in csv_reader.fieldnames]
        if missing_headers:
            return f"Missing required CSV headers: {', '.join(missing_headers)}"
        
        return None
    
    def process_csv_import(self, file) -> Dict[str, Any]:
        """Main method to process CSV import"""
        # Validate file
        validation_result = self.validate_file(file)
        if "error" in validation_result:
            return validation_result
        
        # Read CSV content
        csv_reader, error = self.read_csv_content(file)
        if error:
            return {"error": error}
        
        # Validate headers
        header_error = self.validate_headers(csv_reader)
        if header_error:
            return {"error": header_error}
        
        # Process rows
        processor = CSVRowProcessor(self.db, self.Item, self.user_id)
        return processor.process_rows(csv_reader)


class CSVRowProcessor:
    """Handles processing of individual CSV rows"""
    
    def __init__(self, db_session, item_model, user_id=None):
        self.db = db_session
        self.Item = item_model
        self.user_id = user_id
        
    def process_rows(self, csv_reader: csv.DictReader) -> Dict[str, Any]:
        """Process all rows in the CSV"""
        imported_count = 0
        errors = []
        row_number = 0
        skipped_count = 0
        
        for row in csv_reader:
            row_number += 1
            
            try:
                # Skip empty rows
                if not any(value.strip() for value in row.values() if value):
                    skipped_count += 1
                    continue
                
                # Validate and process row
                validation_errors = self._validate_row(row, row_number)
                if validation_errors:
                    errors.extend(validation_errors)
                    continue
                
                # Create item from row
                item = self._create_item_from_row(row, row_number, errors)
                if item:
                    self.db.add(item)
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_number}: Unexpected error - {str(e)}")
                continue
        
        # Commit changes
        try:
            if imported_count > 0:
                self.db.commit()
                logger.info(f"Bulk import completed: {imported_count} items imported from {row_number} rows")
            else:
                self.db.rollback()
                if not errors:
                    errors.append("No valid data found to import")
        except Exception as e:
            self.db.rollback()
            errors.append(f"Database error during commit: {str(e)}")
            imported_count = 0
        
        return {
            "success": imported_count > 0,
            "imported_count": imported_count,
            "errors": errors,
            "total_rows": row_number,
            "skipped_rows": skipped_count
        }
    
    def _validate_row(self, row: Dict[str, str], row_number: int) -> List[str]:
        """Validate a single row and return list of errors"""
        errors = []
        
        # Validate required fields
        name = row.get('name', '').strip()
        if not name:
            errors.append(f"Row {row_number}: Product name is required")
        
        return errors
    
    def _create_item_from_row(self, row: Dict[str, str], row_number: int, errors: List[str]) -> Optional[Any]:
        """Create an Item instance from a CSV row"""
        validator = CSVDataValidator()
        
        # Extract and validate data
        name = row.get('name', '').strip()
        sku = row.get('sku', '').strip()
        description = row.get('description', '').strip()
        category = row.get('category', 'Uncategorized').strip()
        
        # Validate numeric fields
        quantity = validator.validate_quantity(row.get('quantity', '0'), row_number, errors)
        buying_price = validator.validate_price(row.get('buying_price', '0'), 'buying price', row_number, errors)
        selling_price_retail = validator.validate_price(row.get('selling_price_retail', '0'), 'retail price', row_number, errors)
        selling_price_wholesale = validator.validate_price(row.get('selling_price_wholesale', '0'), 'wholesale price', row_number, errors)
        
        # Validate sales type
        sales_type = validator.validate_sales_type(row.get('sales_type', 'both'), row_number, errors)
        
        # Generate SKU if not provided
        if not sku:
            sku = self.Item.generate_sku(name, category)
        
        # Ensure SKU uniqueness
        sku = self._ensure_unique_sku(sku, row_number, errors)
        
        # Create new item
        try:
            new_item = self.Item(
                name=name,
                sku=sku,
                description=description,
                category=category,
                stock_quantity=quantity,
                buying_price=buying_price,
                retail_price=selling_price_retail,
                wholesale_price=selling_price_wholesale,
                sales_type=sales_type,
                user_id=self.user_id,
                created_at=datetime.utcnow()
            )
            return new_item
        except Exception as e:
            errors.append(f"Row {row_number}: Failed to create item - {str(e)}")
            return None
    
    def _ensure_unique_sku(self, sku: str, row_number: int, errors: List[str]) -> str:
        """Ensure SKU is unique by appending counter if needed"""
        original_sku = sku
        counter = 1
        
        while self.Item.query.filter_by(sku=sku, user_id=self.user_id).first():
            sku = f"{original_sku}-{counter}"
            counter += 1
        
        if sku != original_sku:
            errors.append(f"Row {row_number}: SKU '{original_sku}' already exists, using '{sku}' instead")
        
        return sku


class CSVDataValidator:
    """Handles validation of CSV data fields"""
    
    VALID_SALES_TYPES = ['retail', 'wholesale', 'both']
    
    def validate_quantity(self, quantity_str: str, row_number: int, errors: List[str]) -> int:
        """Validate and return quantity"""
        try:
            if not quantity_str or str(quantity_str).strip().lower() in ['', 'null', 'none']:
                return 0
            
            quantity = int(float(str(quantity_str).strip()))
            if quantity < 0:
                errors.append(f"Row {row_number}: Quantity cannot be negative, setting to 0")
                return 0
            return quantity
        except (ValueError, TypeError):
            errors.append(f"Row {row_number}: Invalid quantity '{quantity_str}', defaulting to 0")
            return 0
    
    def validate_price(self, price_str: str, field_name: str, row_number: int, errors: List[str]) -> float:
        """Validate and return price"""
        try:
            if not price_str or str(price_str).strip().lower() in ['', 'null', 'none']:
                return 0.0
            
            price = float(str(price_str).strip())
            if price < 0:
                errors.append(f"Row {row_number}: {field_name} cannot be negative, setting to 0")
                return 0.0
            return price
        except (ValueError, TypeError):
            errors.append(f"Row {row_number}: Invalid {field_name} '{price_str}', defaulting to 0")
            return 0.0
    
    def validate_sales_type(self, sales_type_str: str, row_number: int, errors: List[str]) -> str:
        """Validate and return sales type"""
        sales_type = str(sales_type_str).strip().lower()
        if sales_type not in self.VALID_SALES_TYPES:
            errors.append(f"Row {row_number}: Invalid sales type, defaulting to 'both'")
            return 'both'
        return sales_type


class CSVTemplateGenerator:
    """Generates CSV templates and examples"""
    
    @staticmethod
    def get_sample_csv_data() -> str:
        """Generate sample CSV data for download"""
        headers = [
            'name', 'sku', 'description', 'category', 'quantity',
            'buying_price', 'selling_price_retail', 'selling_price_wholesale', 'sales_type'
        ]
        
        sample_rows = [
            [
                'iPhone 14', 'IPHONE14', 'Latest iPhone model', 'Electronics', '10',
                '800000', '1000000', '950000', 'both'
            ],
            [
                'Samsung Galaxy', 'GALAXY', 'Latest Samsung phone', 'Electronics', '15',
                '700000', '900000', '850000', 'both'
            ],
            [
                'Laptop Charger', 'CHARGER001', 'Universal laptop charger', 'Accessories', '25',
                '25000', '35000', '32000', 'retail'
            ]
        ]
        
        csv_lines = [','.join(headers)]
        csv_lines.extend([','.join(row) for row in sample_rows])
        
        return '\n'.join(csv_lines)
    
    @staticmethod
    def get_format_instructions() -> Dict[str, Any]:
        """Get CSV format instructions for UI"""
        return {
            "required_fields": ["name"],
            "optional_fields": [
                "sku", "description", "category", "quantity", "buying_price",
                "selling_price_retail", "selling_price_wholesale", "sales_type"
            ],
            "field_descriptions": {
                "name": "Product name (required)",
                "sku": "Stock keeping unit (auto-generated if empty)",
                "description": "Product description",
                "category": "Product category",
                "quantity": "Stock quantity (default: 0)",
                "buying_price": "Purchase price (default: 0)",
                "selling_price_retail": "Retail selling price (default: 0)",
                "selling_price_wholesale": "Wholesale selling price (default: 0)",
                "sales_type": "retail, wholesale, or both (default: both)"
            },
            "example_header": "name,sku,description,category,quantity,buying_price,selling_price_retail,selling_price_wholesale,sales_type",
            "example_row": "iPhone 14,IPHONE14,Latest iPhone model,Electronics,10,800000,1000000,950000,both"
        }
