
import pandas as pd
import io
from models import db, Item, Customer, Supplier
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BulkImportService:
    def __init__(self, user_id):
        self.user_id = user_id

    def import_items_from_csv(self, file_content):
        """Import items from CSV file"""
        try:
            # Read CSV content
            df = pd.read_csv(io.StringIO(file_content))
            
            # Expected columns: name, sku, category, price, cost, stock_quantity, description
            required_columns = ['name', 'price', 'stock_quantity']
            
            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'success': False,
                    'error': f'Missing required columns: {", ".join(missing_columns)}'
                }

            imported_items = []
            errors = []

            for index, row in df.iterrows():
                try:
                    # Check if item already exists
                    existing_item = Item.query.filter_by(
                        name=row['name'],
                        user_id=self.user_id
                    ).first()

                    if existing_item:
                        errors.append(f"Row {index + 1}: Item '{row['name']}' already exists")
                        continue

                    # Create new item
                    new_item = Item(
                        name=row['name'],
                        sku=row.get('sku', ''),
                        category=row.get('category', 'General'),
                        price=float(row['price']),
                        cost=float(row.get('cost', 0)),
                        stock_quantity=int(row['stock_quantity']),
                        description=row.get('description', ''),
                        reorder_level=int(row.get('reorder_level', 10)),
                        user_id=self.user_id,
                        created_at=datetime.utcnow()
                    )

                    db.session.add(new_item)
                    imported_items.append(new_item.name)

                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")

            db.session.commit()

            return {
                'success': True,
                'imported_count': len(imported_items),
                'imported_items': imported_items,
                'errors': errors
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing items from CSV: {str(e)}")
            return {'success': False, 'error': str(e)}

    def import_customers_from_csv(self, file_content):
        """Import customers from CSV file"""
        try:
            df = pd.read_csv(io.StringIO(file_content))
            
            required_columns = ['name', 'phone']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    'success': False,
                    'error': f'Missing required columns: {", ".join(missing_columns)}'
                }

            imported_customers = []
            errors = []

            for index, row in df.iterrows():
                try:
                    # Check if customer already exists
                    existing_customer = Customer.query.filter_by(
                        phone=row['phone'],
                        user_id=self.user_id
                    ).first()

                    if existing_customer:
                        errors.append(f"Row {index + 1}: Customer with phone '{row['phone']}' already exists")
                        continue

                    # Create new customer
                    new_customer = Customer(
                        name=row['name'],
                        phone=row['phone'],
                        email=row.get('email', ''),
                        address=row.get('address', ''),
                        user_id=self.user_id,
                        created_at=datetime.utcnow()
                    )

                    db.session.add(new_customer)
                    imported_customers.append(new_customer.name)

                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")

            db.session.commit()

            return {
                'success': True,
                'imported_count': len(imported_customers),
                'imported_customers': imported_customers,
                'errors': errors
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing customers from CSV: {str(e)}")
            return {'success': False, 'error': str(e)}

    def export_items_to_csv(self):
        """Export items to CSV format"""
        try:
            items = Item.query.filter_by(user_id=self.user_id).all()
            
            data = []
            for item in items:
                data.append({
                    'name': item.name,
                    'sku': item.sku,
                    'category': item.category,
                    'price': item.price,
                    'cost': item.cost,
                    'stock_quantity': item.stock_quantity,
                    'description': item.description,
                    'reorder_level': item.reorder_level
                })

            df = pd.DataFrame(data)
            csv_content = df.to_csv(index=False)

            return {
                'success': True,
                'csv_content': csv_content,
                'item_count': len(items)
            }

        except Exception as e:
            logger.error(f"Error exporting items to CSV: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_import_template(self, data_type='items'):
        """Get CSV template for import"""
        templates = {
            'items': {
                'columns': ['name', 'sku', 'category', 'price', 'cost', 'stock_quantity', 'description', 'reorder_level'],
                'sample_data': [
                    ['Sample Product', 'SKU001', 'Electronics', '100.00', '70.00', '50', 'Sample description', '10']
                ]
            },
            'customers': {
                'columns': ['name', 'phone', 'email', 'address'],
                'sample_data': [
                    ['John Doe', '+255123456789', 'john@example.com', '123 Main St']
                ]
            }
        }

        if data_type not in templates:
            return {'success': False, 'error': 'Invalid template type'}

        template = templates[data_type]
        df = pd.DataFrame([template['sample_data'][0]], columns=template['columns'])
        csv_content = df.to_csv(index=False)

        return {
            'success': True,
            'csv_content': csv_content,
            'columns': template['columns']
        }
