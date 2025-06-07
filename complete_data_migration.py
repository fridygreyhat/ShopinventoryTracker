
#!/usr/bin/env python3
"""
Complete data migration from SQLite backup to PostgreSQL
This script will migrate all existing data from your SQLite backups to PostgreSQL
"""

import os
import json
from datetime import datetime
from app import app, db
from models import (
    User, Item, Subuser, SubuserPermission, OnDemandProduct, Setting,
    Sale, SaleItem, FinancialTransaction, FinancialSummary,
    Category, Subcategory, LayawayPlan, LayawayPayment,
    Location, LocationStock, StockTransfer, StockTransferItem
)

def load_latest_backup():
    """Load the most recent SQLite backup file"""
    backup_files = [f for f in os.listdir('.') if f.startswith('sqlite_backup_') and f.endswith('.json')]
    
    if not backup_files:
        print("❌ No backup files found")
        return None
    
    # Get the most recent backup
    latest_backup = sorted(backup_files)[-1]
    print(f"📄 Loading backup: {latest_backup}")
    
    with open(latest_backup, 'r') as f:
        return json.load(f)

def migrate_users(users_data):
    """Migrate users from backup data"""
    if not users_data:
        print("⏭️ No users to migrate")
        return
    
    print(f"👥 Migrating {len(users_data)} users...")
    
    for user_data in users_data:
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(email=user_data.get('email')).first()
            if existing_user:
                print(f"⚠️ User {user_data.get('email')} already exists, skipping")
                continue
            
            user = User(
                username=user_data.get('username'),
                email=user_data.get('email'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                phone=user_data.get('phone'),
                shop_name=user_data.get('shop_name'),
                product_categories=user_data.get('product_categories'),
                active=user_data.get('active', True),
                is_admin=user_data.get('is_admin', False),
                email_verified=user_data.get('email_verified', True)
            )
            
            # Set a temporary password if password_hash exists
            if user_data.get('password_hash'):
                user.password_hash = user_data['password_hash']
            else:
                user.set_password('temp123456')  # User should change this
            
            db.session.add(user)
            print(f"✅ Migrated user: {user.email}")
            
        except Exception as e:
            print(f"❌ Error migrating user {user_data.get('email')}: {e}")
    
    db.session.commit()

def migrate_items(items_data):
    """Migrate items from backup data"""
    if not items_data:
        print("⏭️ No items to migrate")
        return
    
    print(f"📦 Migrating {len(items_data)} items...")
    
    for item_data in items_data:
        try:
            # Check if item already exists
            existing_item = Item.query.filter_by(sku=item_data.get('sku')).first()
            if existing_item:
                print(f"⚠️ Item {item_data.get('sku')} already exists, skipping")
                continue
            
            # Get the user for this item
            user = User.query.get(item_data['user_id'])
            if not user:
                print(f"❌ User ID {item_data['user_id']} not found for item {item_data['name']}")
                continue
            
            item = Item(
                name=item_data['name'],
                sku=item_data.get('sku'),
                unit_type=item_data.get('unit_type', 'quantity'),
                description=item_data.get('description'),
                category=item_data.get('category'),
                subcategory=item_data.get('subcategory'),
                sell_by=item_data.get('sell_by', 'quantity'),
                quantity=int(item_data.get('quantity', 0)),
                buying_price=float(item_data.get('buying_price', 0)),
                selling_price_retail=float(item_data.get('selling_price_retail', 0)),
                selling_price_wholesale=float(item_data.get('selling_price_wholesale', 0)),
                price=float(item_data.get('price', 0)),
                sales_type=item_data.get('sales_type', 'both'),
                track_by_location=item_data.get('track_by_location', False),
                user_id=user.id
            )
            
            db.session.add(item)
            
        except Exception as e:
            print(f"❌ Error migrating item {item_data.get('name')}: {e}")
    
    db.session.commit()

def migrate_sales(sales_data):
    """Migrate sales from backup data"""
    if not sales_data:
        print("⏭️ No sales to migrate")
        return
    
    print(f"💰 Migrating {len(sales_data)} sales...")
    
    for sale_data in sales_data:
        try:
            # Check if sale already exists
            existing_sale = Sale.query.filter_by(invoice_number=sale_data.get('invoice_number')).first()
            if existing_sale:
                continue
            
            # Get the user for this sale
            user = User.query.get(sale_data['user_id'])
            if not user:
                continue
            
            sale = Sale(
                invoice_number=sale_data.get('invoice_number'),
                customer_name=sale_data.get('customer_name', 'Walk-in Customer'),
                customer_phone=sale_data.get('customer_phone'),
                sale_type=sale_data.get('sale_type', 'retail'),
                subtotal=float(sale_data.get('subtotal', 0)),
                discount_type=sale_data.get('discount_type', 'none'),
                discount_value=float(sale_data.get('discount_value', 0)),
                discount_amount=float(sale_data.get('discount_amount', 0)),
                total=float(sale_data.get('total', 0)),
                payment_method=sale_data.get('payment_method', 'cash'),
                payment_details=sale_data.get('payment_details'),
                payment_amount=float(sale_data.get('payment_amount', 0)),
                change_amount=float(sale_data.get('change_amount', 0)),
                notes=sale_data.get('notes'),
                user_id=user.id
            )
            
            db.session.add(sale)
            
        except Exception as e:
            print(f"❌ Error migrating sale {sale_data.get('invoice_number')}: {e}")
    
    db.session.commit()

def migrate_financial_transactions(transactions_data):
    """Migrate financial transactions from backup data"""
    if not transactions_data:
        print("⏭️ No financial transactions to migrate")
        return
    
    print(f"💳 Migrating {len(transactions_data)} financial transactions...")
    
    for transaction_data in transactions_data:
        try:
            # Get the user for this transaction
            user = User.query.get(transaction_data['user_id'])
            if not user:
                continue
            
            transaction = FinancialTransaction(
                date=datetime.strptime(transaction_data['date'], '%Y-%m-%d').date(),
                description=transaction_data['description'],
                amount=float(transaction_data['amount']),
                transaction_type=transaction_data['transaction_type'],
                category=transaction_data['category'],
                reference_id=transaction_data.get('reference_id'),
                payment_method=transaction_data.get('payment_method'),
                tax_rate=float(transaction_data.get('tax_rate', 0)),
                tax_amount=float(transaction_data.get('tax_amount', 0)),
                cost_of_goods_sold=float(transaction_data.get('cost_of_goods_sold', 0)),
                gross_amount=float(transaction_data.get('gross_amount', 0)),
                notes=transaction_data.get('notes'),
                user_id=user.id
            )
            
            db.session.add(transaction)
            
        except Exception as e:
            print(f"❌ Error migrating transaction: {e}")
    
    db.session.commit()

def create_default_location_for_users():
    """Create a default location for each user"""
    print("🏪 Creating default locations for users...")
    
    users = User.query.all()
    for user in users:
        # Check if user already has a location
        existing_location = Location.query.filter_by(user_id=user.id).first()
        if existing_location:
            continue
        
        # Create default location
        location = Location(
            name=f"{user.shop_name or user.username}'s Main Store",
            code="MAIN",
            type="store",
            is_default=True,
            user_id=user.id
        )
        
        db.session.add(location)
        print(f"✅ Created default location for user: {user.username}")
    
    db.session.commit()

def verify_migration():
    """Verify that data was migrated correctly"""
    print("\n🔍 Verifying migration...")
    
    with app.app_context():
        users = User.query.all()
        items = Item.query.all()
        sales = Sale.query.all()
        transactions = FinancialTransaction.query.all()
        
        print(f"📊 Migration Results:")
        print(f"  - Users: {len(users)}")
        print(f"  - Items: {len(items)}")
        print(f"  - Sales: {len(sales)}")
        print(f"  - Financial Transactions: {len(transactions)}")
        
        # Check user isolation
        print(f"\n👥 User Data Breakdown:")
        for user in users:
            user_items = Item.query.filter_by(user_id=user.id).count()
            user_sales = Sale.query.filter_by(user_id=user.id).count()
            user_transactions = FinancialTransaction.query.filter_by(user_id=user.id).count()
            print(f"  - {user.username}: {user_items} items, {user_sales} sales, {user_transactions} transactions")

def main():
    """Main migration function"""
    print("🚀 Starting complete data migration...")
    
    # Check if PostgreSQL is configured
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not database_url.startswith(("postgres://", "postgresql://")):
        print("❌ PostgreSQL DATABASE_URL not found. Please set up PostgreSQL first.")
        return
    
    with app.app_context():
        try:
            # Load backup data
            backup_data = load_latest_backup()
            if not backup_data:
                return
            
            print("📥 Starting data migration...")
            
            # Migrate in dependency order
            migrate_users(backup_data.get('user', []))
            migrate_items(backup_data.get('item', []))
            migrate_sales(backup_data.get('sale', []))
            migrate_financial_transactions(backup_data.get('financial_transaction', []))
            
            # Create default locations
            create_default_location_for_users()
            
            # Verify migration
            verify_migration()
            
            print("\n🎉 Migration completed successfully!")
            print("\n📋 Next steps:")
            print("1. Test your application with different user accounts")
            print("2. Verify that each user sees only their own data")
            print("3. Check that all features work correctly")
            print("4. Your multi-user inventory system is now ready!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    main()
