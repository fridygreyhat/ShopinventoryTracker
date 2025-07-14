
#!/usr/bin/env python3
"""
Database repair and schema alignment script
"""

from app import app, db
from extensions import configure_database
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_database():
    """Repair database schema and relationships"""
    with app.app_context():
        try:
            # Import all models
            from models import (User, Item, Setting, Sale, SaleItem, FinancialTransaction, 
                Category, Customer, OnDemandProduct, StockMovement, ChartOfAccounts,
                Journal, Supplier, PurchaseOrder, UserTwoFactor, Employee, InstallmentPlan
            )
            
            logger.info("Starting database repair...")
            
            # Drop and recreate all tables (BE CAREFUL - THIS WILL DELETE DATA)
            # Only use this if you want to start fresh
            # db.drop_all()
            
            # Create all tables
            db.create_all()
            logger.info("All tables created successfully")
            
            # Add foreign key constraints if missing
            repair_constraints()
            
            # Add missing indexes
            add_missing_indexes()
            
            logger.info("Database repair completed successfully")
            
        except Exception as e:
            logger.error(f"Database repair failed: {str(e)}")
            db.session.rollback()
            raise

def repair_constraints():
    """Add missing foreign key constraints"""
    try:
        # Add foreign key constraints
        constraints = [
            "ALTER TABLE item ADD CONSTRAINT fk_item_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE item ADD CONSTRAINT fk_item_category FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL;",
            "ALTER TABLE sale ADD CONSTRAINT fk_sale_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE sale ADD CONSTRAINT fk_sale_customer FOREIGN KEY (customer_id) REFERENCES customer(id) ON DELETE SET NULL;",
            "ALTER TABLE sale_item ADD CONSTRAINT fk_sale_item_sale FOREIGN KEY (sale_id) REFERENCES sale(id) ON DELETE CASCADE;",
            "ALTER TABLE sale_item ADD CONSTRAINT fk_sale_item_item FOREIGN KEY (item_id) REFERENCES item(id) ON DELETE CASCADE;",
            "ALTER TABLE stock_movement ADD CONSTRAINT fk_stock_movement_item FOREIGN KEY (item_id) REFERENCES item(id) ON DELETE CASCADE;",
            "ALTER TABLE stock_movement ADD CONSTRAINT fk_stock_movement_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE category ADD CONSTRAINT fk_category_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE category ADD CONSTRAINT fk_category_parent FOREIGN KEY (parent_id) REFERENCES category(id) ON DELETE SET NULL;",
            "ALTER TABLE customer ADD CONSTRAINT fk_customer_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE financial_transaction ADD CONSTRAINT fk_financial_transaction_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE supplier ADD CONSTRAINT fk_supplier_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE purchase_order ADD CONSTRAINT fk_purchase_order_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE purchase_order ADD CONSTRAINT fk_purchase_order_supplier FOREIGN KEY (supplier_id) REFERENCES supplier(id) ON DELETE CASCADE;",
            "ALTER TABLE installment_plan ADD CONSTRAINT fk_installment_plan_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE installment_plan ADD CONSTRAINT fk_installment_plan_sale FOREIGN KEY (sale_id) REFERENCES sale(id) ON DELETE CASCADE;",
            "ALTER TABLE chart_of_accounts ADD CONSTRAINT fk_chart_of_accounts_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;",
            "ALTER TABLE journal ADD CONSTRAINT fk_journal_user FOREIGN KEY (user_id) REFERENCES \"user\"(id) ON DELETE CASCADE;"
        ]
        
        for constraint in constraints:
            try:
                db.session.execute(db.text(constraint))
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning(f"Could not add constraint: {str(e)}")
        
        db.session.commit()
        logger.info("Foreign key constraints added successfully")
        
    except Exception as e:
        logger.error(f"Error adding constraints: {str(e)}")
        db.session.rollback()

def add_missing_indexes():
    """Add missing database indexes for performance"""
    try:
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_item_user_id ON item(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_item_category_id ON item(category_id);",
            "CREATE INDEX IF NOT EXISTS idx_item_is_active ON item(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_sale_user_id ON sale(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_sale_created_at ON sale(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_sale_payment_status ON sale(payment_status);",
            "CREATE INDEX IF NOT EXISTS idx_sale_item_sale_id ON sale_item(sale_id);",
            "CREATE INDEX IF NOT EXISTS idx_sale_item_item_id ON sale_item(item_id);",
            "CREATE INDEX IF NOT EXISTS idx_stock_movement_item_id ON stock_movement(item_id);",
            "CREATE INDEX IF NOT EXISTS idx_financial_transaction_user_id ON financial_transaction(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_financial_transaction_date ON financial_transaction(date);",
            "CREATE INDEX IF NOT EXISTS idx_category_user_id ON category(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_customer_user_id ON customer(user_id);"
        ]
        
        for index in indexes:
            try:
                db.session.execute(db.text(index))
            except Exception as e:
                logger.warning(f"Could not add index: {str(e)}")
        
        db.session.commit()
        logger.info("Database indexes added successfully")
        
    except Exception as e:
        logger.error(f"Error adding indexes: {str(e)}")
        db.session.rollback()

if __name__ == '__main__':
    # Configure database
    configure_database(app)
    
    # Run repair
    repair_database()
    
    print("Database repair completed!")
