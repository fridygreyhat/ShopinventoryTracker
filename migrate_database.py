
#!/usr/bin/env python3
"""
Database migration script to fix schema issues
"""

import os
import logging
from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run database migration to fix schema issues"""
    try:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL environment variable not found")
            return False
        
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            logger.info("Starting database migration...")
            
            # Start transaction
            trans = conn.begin()
            
            try:
                # Add missing columns to sale table
                logger.info("Adding missing columns to sale table...")
                
                # Check and add customer_id
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'sale' AND column_name = 'customer_id'
                """))
                if not result.fetchone():
                    conn.execute(text("ALTER TABLE sale ADD COLUMN customer_id INTEGER"))
                    logger.info("Added customer_id column to sale table")
                
                # Check and add payment_type
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'sale' AND column_name = 'payment_type'
                """))
                if not result.fetchone():
                    conn.execute(text("ALTER TABLE sale ADD COLUMN payment_type VARCHAR(20) DEFAULT 'cash'"))
                    conn.execute(text("UPDATE sale SET payment_type = 'cash' WHERE payment_type IS NULL"))
                    logger.info("Added payment_type column to sale table")
                
                # Check and add payment_status
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'sale' AND column_name = 'payment_status'
                """))
                if not result.fetchone():
                    conn.execute(text("ALTER TABLE sale ADD COLUMN payment_status VARCHAR(20) DEFAULT 'completed'"))
                    conn.execute(text("UPDATE sale SET payment_status = 'completed' WHERE payment_status IS NULL"))
                    logger.info("Added payment_status column to sale table")
                
                # Check and add sale_number
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'sale' AND column_name = 'sale_number'
                """))
                if not result.fetchone():
                    conn.execute(text("ALTER TABLE sale ADD COLUMN sale_number VARCHAR(50)"))
                    logger.info("Added sale_number column to sale table")
                
                # Add user_id to financial_transaction if missing
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'financial_transaction' AND column_name = 'user_id'
                """))
                if not result.fetchone():
                    conn.execute(text("ALTER TABLE financial_transaction ADD COLUMN user_id INTEGER"))
                    logger.info("Added user_id column to financial_transaction table")
                
                # Commit the transaction
                trans.commit()
                logger.info("Database migration completed successfully!")
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"Migration failed: {str(e)}")
                return False
                
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    run_migration()
