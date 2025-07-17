
#!/usr/bin/env python3
"""
Database repair script to fix authentication and schema issues
"""

import os
import logging
from app import app, db
from extensions import configure_database

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_database():
    """Repair database issues"""
    with app.app_context():
        try:
            logger.info("Starting database repair...")
            
            # Import all models
            from models import (User, Item, Setting, Sale, SaleItem, FinancialTransaction, 
                Category, Customer, OnDemandProduct, StockMovement, ChartOfAccounts,
                Journal, Supplier, PurchaseOrder, UserTwoFactor, Employee, InstallmentSale, InstallmentPayment
            )
            
            # Test connection
            try:
                db.session.execute(db.text('SELECT 1'))
                db.session.commit()
                logger.info("✅ Database connection successful")
            except Exception as e:
                logger.error(f"❌ Database connection failed: {str(e)}")
                return False
            
            # Create all tables
            db.create_all()
            logger.info("✅ Database tables created/updated")
            
            # Add missing columns safely
            def add_column_if_not_exists(table_name, column_name, column_def):
                try:
                    result = db.session.execute(db.text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' 
                        AND column_name = '{column_name}'
                    """))
                    
                    if not result.fetchone():
                        db.session.execute(db.text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"))
                        db.session.commit()
                        logger.info(f"✅ Added column {column_name} to {table_name}")
                    else:
                        logger.info(f"Column {column_name} already exists in {table_name}")
                except Exception as e:
                    logger.warning(f"Could not add column {column_name}: {str(e)}")
                    db.session.rollback()
            
            # Fix common missing columns
            add_column_if_not_exists('user', 'is_active', 'BOOLEAN DEFAULT TRUE')
            add_column_if_not_exists('user', 'phone', 'VARCHAR(20)')
            add_column_if_not_exists('item', 'is_active', 'BOOLEAN DEFAULT TRUE')
            add_column_if_not_exists('sale', 'is_installment', 'BOOLEAN DEFAULT FALSE')
            add_column_if_not_exists('sale', 'down_payment', 'FLOAT DEFAULT 0')
            add_column_if_not_exists('sale', 'installment_months', 'INTEGER DEFAULT 0')
            add_column_if_not_exists('sale', 'monthly_payment', 'FLOAT DEFAULT 0')
            
            # Create default admin user if none exists
            admin_user = User.query.filter_by(is_admin=True).first()
            if not admin_user:
                admin = User(
                    username='admin',
                    email='admin@inventory.com',
                    first_name='Admin',
                    last_name='User',
                    is_admin=True,
                    is_active=True,
                    email_verified=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                logger.info("✅ Created default admin user (admin@inventory.com / admin123)")
            
            logger.info("✅ Database repair completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database repair failed: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    # Configure database
    configure_database(app)
    
    # Run repair
    success = repair_database()
    
    if success:
        print("✅ Database repair completed successfully!")
        print("You can now try logging in with:")
        print("Email: admin@inventory.com")
        print("Password: admin123")
    else:
        print("❌ Database repair failed!")
