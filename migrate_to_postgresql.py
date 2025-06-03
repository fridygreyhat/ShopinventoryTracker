
#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL
Run this script after setting up your PostgreSQL database in Replit
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from app import app, db
from models import (
    User, Item, Subuser, SubuserPermission, OnDemandProduct, Setting,
    Sale, SaleItem, FinancialTransaction, FinancialSummary,
    Category, Subcategory, LayawayPlan, LayawayPayment,
    Location, LocationStock, StockTransfer, StockTransferItem
)

def export_sqlite_data():
    """Export data from SQLite database"""
    sqlite_path = "instance/inventory.db"
    
    if not os.path.exists(sqlite_path):
        print("❌ SQLite database not found at instance/inventory.db")
        return None
    
    print("📊 Exporting data from SQLite...")
    
    # Connect to SQLite
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()
    
    exported_data = {}
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"Found {len(tables)} tables to export: {', '.join(tables)}")
    
    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            exported_data[table] = [dict(row) for row in rows]
            print(f"✅ Exported {len(rows)} records from {table}")
        except Exception as e:
            print(f"⚠️ Error exporting {table}: {e}")
            exported_data[table] = []
    
    conn.close()
    return exported_data

def import_to_postgresql(data):
    """Import data to PostgreSQL database"""
    with app.app_context():
        print("🔄 Creating PostgreSQL tables...")
        
        # Create all tables
        db.create_all()
        print("✅ Tables created successfully")
        
        # Import data in dependency order
        import_order = [
            'user', 'category', 'subcategory', 'location', 'item', 'location_stock',
            'subuser', 'subuser_permission', 'on_demand_product', 'setting',
            'sale', 'sale_item', 'financial_transaction', 'financial_summary',
            'layaway_plan', 'layaway_payment', 'stock_transfer', 'stock_transfer_item'
        ]
        
        total_records = 0
        
        for table_name in import_order:
            if table_name not in data:
                continue
                
            records = data[table_name]
            if not records:
                print(f"⏭️ Skipping {table_name} (no data)")
                continue
            
            print(f"📥 Importing {len(records)} records to {table_name}...")
            
            try:
                if table_name == 'user':
                    import_users(records)
                elif table_name == 'item':
                    import_items(records)
                elif table_name == 'category':
                    import_categories(records)
                elif table_name == 'subcategory':
                    import_subcategories(records)
                elif table_name == 'location':
                    import_locations(records)
                elif table_name == 'location_stock':
                    import_location_stock(records)
                elif table_name == 'subuser':
                    import_subusers(records)
                elif table_name == 'subuser_permission':
                    import_subuser_permissions(records)
                elif table_name == 'on_demand_product':
                    import_on_demand_products(records)
                elif table_name == 'setting':
                    import_settings(records)
                elif table_name == 'sale':
                    import_sales(records)
                elif table_name == 'sale_item':
                    import_sale_items(records)
                elif table_name == 'financial_transaction':
                    import_financial_transactions(records)
                elif table_name == 'financial_summary':
                    import_financial_summaries(records)
                elif table_name == 'layaway_plan':
                    import_layaway_plans(records)
                elif table_name == 'layaway_payment':
                    import_layaway_payments(records)
                elif table_name == 'stock_transfer':
                    import_stock_transfers(records)
                elif table_name == 'stock_transfer_item':
                    import_stock_transfer_items(records)
                
                total_records += len(records)
                print(f"✅ Successfully imported {len(records)} {table_name} records")
                
            except Exception as e:
                print(f"❌ Error importing {table_name}: {e}")
                # Continue with other tables
                continue
        
        print(f"🎉 Migration completed! Total records imported: {total_records}")

def import_users(records):
    """Import user records"""
    for record in records:
        user = User(
            id=record['id'],
            username=record['username'],
            email=record['email'],
            password_hash=record.get('password_hash'),
            firebase_uid=record.get('firebase_uid'),
            email_verified=bool(record.get('email_verified', False)),
            verification_token=record.get('verification_token'),
            verification_token_expires=datetime.fromisoformat(record['verification_token_expires']) if record.get('verification_token_expires') else None,
            first_name=record.get('first_name'),
            last_name=record.get('last_name'),
            phone=record.get('phone'),
            shop_name=record.get('shop_name'),
            product_categories=record.get('product_categories'),
            active=bool(record.get('active', True)),
            is_active=bool(record.get('is_active', True)),
            is_admin=bool(record.get('is_admin', False)),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow(),
            last_login=datetime.fromisoformat(record['last_login']) if record.get('last_login') else None
        )
        db.session.merge(user)
    db.session.commit()

def import_items(records):
    """Import item records"""
    for record in records:
        item = Item(
            id=record['id'],
            name=record['name'],
            sku=record.get('sku'),
            unit_type=record.get('unit_type', 'quantity'),
            description=record.get('description'),
            category=record.get('category'),
            category_id=record.get('category_id'),
            subcategory=record.get('subcategory'),
            sell_by=record.get('sell_by', 'quantity'),
            quantity=int(record.get('quantity', 0)),
            buying_price=float(record.get('buying_price', 0)),
            selling_price_retail=float(record.get('selling_price_retail', 0)),
            selling_price_wholesale=float(record.get('selling_price_wholesale', 0)),
            price=float(record.get('price', 0)),
            sales_type=record.get('sales_type', 'both'),
            track_by_location=bool(record.get('track_by_location', False)),
            user_id=record['user_id'],
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(item)
    db.session.commit()

def import_categories(records):
    """Import category records"""
    for record in records:
        category = Category(
            id=record['id'],
            name=record['name'],
            description=record.get('description'),
            icon=record.get('icon'),
            color=record.get('color', '#007bff'),
            is_active=bool(record.get('is_active', True)),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(category)
    db.session.commit()

def import_subcategories(records):
    """Import subcategory records"""
    for record in records:
        subcategory = Subcategory(
            id=record['id'],
            name=record['name'],
            description=record.get('description'),
            category_id=record['category_id'],
            is_active=bool(record.get('is_active', True)),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(subcategory)
    db.session.commit()

def import_locations(records):
    """Import location records"""
    for record in records:
        location = Location(
            id=record['id'],
            name=record['name'],
            code=record['code'],
            type=record.get('type', 'warehouse'),
            address=record.get('address'),
            city=record.get('city'),
            state=record.get('state'),
            postal_code=record.get('postal_code'),
            country=record.get('country'),
            phone=record.get('phone'),
            email=record.get('email'),
            manager_name=record.get('manager_name'),
            is_active=bool(record.get('is_active', True)),
            is_default=bool(record.get('is_default', False)),
            user_id=record['user_id'],
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(location)
    db.session.commit()

def import_location_stock(records):
    """Import location stock records"""
    for record in records:
        stock = LocationStock(
            id=record['id'],
            item_id=record['item_id'],
            location_id=record['location_id'],
            quantity=int(record.get('quantity', 0)),
            reserved_quantity=int(record.get('reserved_quantity', 0)),
            min_stock_level=int(record.get('min_stock_level', 0)),
            max_stock_level=int(record.get('max_stock_level', 0)),
            last_updated=datetime.fromisoformat(record['last_updated']) if record.get('last_updated') else datetime.utcnow()
        )
        db.session.merge(stock)
    db.session.commit()

def import_subusers(records):
    """Import subuser records"""
    for record in records:
        subuser = Subuser(
            id=record['id'],
            name=record['name'],
            email=record['email'],
            password_hash=record['password_hash'],
            parent_user_id=record['parent_user_id'],
            is_active=bool(record.get('is_active', True)),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(subuser)
    db.session.commit()

def import_subuser_permissions(records):
    """Import subuser permission records"""
    for record in records:
        permission = SubuserPermission(
            id=record['id'],
            subuser_id=record['subuser_id'],
            permission=record['permission'],
            granted=bool(record.get('granted', True)),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(permission)
    db.session.commit()

def import_on_demand_products(records):
    """Import on-demand product records"""
    for record in records:
        product = OnDemandProduct(
            id=record['id'],
            name=record['name'],
            description=record.get('description'),
            base_price=float(record.get('base_price', 0)),
            production_time=int(record.get('production_time', 0)),
            category=record.get('category'),
            materials=record.get('materials'),
            is_active=bool(record.get('is_active', True)),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(product)
    db.session.commit()

def import_settings(records):
    """Import setting records"""
    for record in records:
        setting = Setting(
            id=record['id'],
            key=record['key'],
            value=record.get('value'),
            description=record.get('description'),
            category=record.get('category', 'general'),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(setting)
    db.session.commit()

def import_sales(records):
    """Import sale records"""
    for record in records:
        sale = Sale(
            id=record['id'],
            invoice_number=record.get('invoice_number'),
            customer_name=record.get('customer_name', 'Walk-in Customer'),
            customer_phone=record.get('customer_phone'),
            sale_type=record.get('sale_type', 'retail'),
            subtotal=float(record.get('subtotal', 0)),
            discount_type=record.get('discount_type', 'none'),
            discount_value=float(record.get('discount_value', 0)),
            discount_amount=float(record.get('discount_amount', 0)),
            total=float(record.get('total', 0)),
            payment_method=record.get('payment_method', 'cash'),
            payment_details=record.get('payment_details'),
            payment_amount=float(record.get('payment_amount', 0)),
            change_amount=float(record.get('change_amount', 0)),
            notes=record.get('notes'),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(sale)
    db.session.commit()

def import_sale_items(records):
    """Import sale item records"""
    for record in records:
        sale_item = SaleItem(
            id=record['id'],
            sale_id=record['sale_id'],
            item_id=record.get('item_id'),
            product_name=record['product_name'],
            product_sku=record.get('product_sku'),
            price=float(record.get('price', 0)),
            quantity=int(record.get('quantity', 1)),
            total=float(record.get('total', 0)),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow()
        )
        db.session.merge(sale_item)
    db.session.commit()

def import_financial_transactions(records):
    """Import financial transaction records"""
    for record in records:
        transaction = FinancialTransaction(
            id=record['id'],
            date=datetime.fromisoformat(record['date']).date() if record.get('date') else datetime.utcnow().date(),
            description=record['description'],
            amount=float(record['amount']),
            transaction_type=record['transaction_type'],
            category=record['category'],
            reference_id=record.get('reference_id'),
            payment_method=record.get('payment_method'),
            tax_rate=float(record.get('tax_rate', 0)),
            tax_amount=float(record.get('tax_amount', 0)),
            cost_of_goods_sold=float(record.get('cost_of_goods_sold', 0)),
            gross_amount=float(record.get('gross_amount', 0)),
            notes=record.get('notes'),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(transaction)
    db.session.commit()

def import_financial_summaries(records):
    """Import financial summary records"""
    for record in records:
        summary = FinancialSummary(
            id=record['id'],
            period_type=record['period_type'],
            period_start=datetime.fromisoformat(record['period_start']).date(),
            period_end=datetime.fromisoformat(record['period_end']).date(),
            total_income=float(record.get('total_income', 0)),
            total_expenses=float(record.get('total_expenses', 0)),
            net_profit=float(record.get('net_profit', 0)),
            summary_data=record.get('summary_data'),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(summary)
    db.session.commit()

def import_layaway_plans(records):
    """Import layaway plan records"""
    for record in records:
        plan = LayawayPlan(
            id=record['id'],
            customer_name=record['customer_name'],
            customer_phone=record.get('customer_phone'),
            customer_email=record.get('customer_email'),
            total_amount=float(record['total_amount']),
            down_payment=float(record.get('down_payment', 0)),
            remaining_balance=float(record['remaining_balance']),
            installment_amount=float(record['installment_amount']),
            payment_frequency=record.get('payment_frequency', 'monthly'),
            next_payment_date=datetime.fromisoformat(record['next_payment_date']).date() if record.get('next_payment_date') else None,
            completion_date=datetime.fromisoformat(record['completion_date']).date() if record.get('completion_date') else None,
            status=record.get('status', 'active'),
            items_data=record.get('items_data'),
            notes=record.get('notes'),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(plan)
    db.session.commit()

def import_layaway_payments(records):
    """Import layaway payment records"""
    for record in records:
        payment = LayawayPayment(
            id=record['id'],
            layaway_plan_id=record['layaway_plan_id'],
            amount=float(record['amount']),
            payment_method=record.get('payment_method', 'cash'),
            payment_date=datetime.fromisoformat(record['payment_date']).date() if record.get('payment_date') else datetime.utcnow().date(),
            reference_number=record.get('reference_number'),
            notes=record.get('notes'),
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow()
        )
        db.session.merge(payment)
    db.session.commit()

def import_stock_transfers(records):
    """Import stock transfer records"""
    for record in records:
        transfer = StockTransfer(
            id=record['id'],
            transfer_number=record['transfer_number'],
            from_location_id=record['from_location_id'],
            to_location_id=record['to_location_id'],
            status=record.get('status', 'pending'),
            transfer_date=datetime.fromisoformat(record['transfer_date']).date() if record.get('transfer_date') else datetime.utcnow().date(),
            expected_arrival=datetime.fromisoformat(record['expected_arrival']).date() if record.get('expected_arrival') else None,
            actual_arrival=datetime.fromisoformat(record['actual_arrival']).date() if record.get('actual_arrival') else None,
            notes=record.get('notes'),
            requested_by=record.get('requested_by'),
            approved_by=record.get('approved_by'),
            created_by=record['created_by'],
            created_at=datetime.fromisoformat(record['created_at']) if record.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(record['updated_at']) if record.get('updated_at') else datetime.utcnow()
        )
        db.session.merge(transfer)
    db.session.commit()

def import_stock_transfer_items(records):
    """Import stock transfer item records"""
    for record in records:
        item = StockTransferItem(
            id=record['id'],
            transfer_id=record['transfer_id'],
            item_id=record['item_id'],
            quantity_requested=int(record['quantity_requested']),
            quantity_shipped=int(record.get('quantity_shipped', 0)),
            quantity_received=int(record.get('quantity_received', 0)),
            notes=record.get('notes')
        )
        db.session.merge(item)
    db.session.commit()

def main():
    """Main migration function"""
    print("🚀 Starting SQLite to PostgreSQL migration...")
    
    # Check if PostgreSQL URL is set
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not database_url.startswith(("postgres://", "postgresql://")):
        print("❌ PostgreSQL DATABASE_URL not found in environment variables.")
        print("Please create a PostgreSQL database in Replit first.")
        return
    
    print(f"✅ PostgreSQL database URL found")
    
    # Export from SQLite
    sqlite_data = export_sqlite_data()
    if not sqlite_data:
        print("❌ Failed to export SQLite data")
        return
    
    # Backup exported data
    backup_file = f"sqlite_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_file, 'w') as f:
        json.dump(sqlite_data, f, indent=2, default=str)
    print(f"💾 Backup saved to {backup_file}")
    
    # Import to PostgreSQL
    try:
        import_to_postgresql(sqlite_data)
        print("🎉 Migration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Test your application to ensure everything works")
        print("2. Remove the SQLite database file if everything looks good")
        print("3. Your app is now running on PostgreSQL!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print(f"💾 Your data backup is saved in {backup_file}")
        raise

if __name__ == "__main__":
    main()
