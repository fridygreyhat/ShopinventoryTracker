
#!/usr/bin/env python3
"""
Database repair script to fix login and user data issues
"""

from app import app, db
from models import User, Item, Sale, FinancialTransaction
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_database():
    """Repair database issues that cause login failures"""
    with app.app_context():
        try:
            logger.info("Starting database repair...")
            
            # 1. Ensure all users have required fields
            users = User.query.all()
            for user in users:
                if not hasattr(user, 'active') or user.active is None:
                    user.active = True
                if not hasattr(user, 'is_active') or user.is_active is None:
                    user.is_active = True
                if not hasattr(user, 'role') or user.role is None:
                    user.role = 'viewer'
                if not hasattr(user, 'email_verified') or user.email_verified is None:
                    user.email_verified = False
                
                # Ensure password hash exists for non-Firebase users
                if not user.password_hash and not user.firebase_uid:
                    from werkzeug.security import generate_password_hash
                    user.password_hash = generate_password_hash('default123')
                
                logger.info(f"Repaired user: {user.username}")
            
            db.session.commit()
            logger.info("User repairs completed")
            
            # 2. Ensure all items have user_id
            orphaned_items = Item.query.filter_by(user_id=None).all()
            if orphaned_items:
                # Get first admin or any user
                admin_user = User.query.filter_by(is_admin=True).first()
                if not admin_user:
                    admin_user = User.query.first()
                
                if admin_user:
                    for item in orphaned_items:
                        item.user_id = admin_user.id
                    db.session.commit()
                    logger.info(f"Assigned {len(orphaned_items)} orphaned items to {admin_user.username}")
            
            # 3. Ensure all sales have user_id
            orphaned_sales = Sale.query.filter_by(user_id=None).all()
            if orphaned_sales:
                admin_user = User.query.filter_by(is_admin=True).first()
                if not admin_user:
                    admin_user = User.query.first()
                
                if admin_user:
                    for sale in orphaned_sales:
                        sale.user_id = admin_user.id
                    db.session.commit()
                    logger.info(f"Assigned {len(orphaned_sales)} orphaned sales to {admin_user.username}")
            
            # 4. Ensure all financial transactions have user_id
            orphaned_transactions = FinancialTransaction.query.filter_by(user_id=None).all()
            if orphaned_transactions:
                admin_user = User.query.filter_by(is_admin=True).first()
                if not admin_user:
                    admin_user = User.query.first()
                
                if admin_user:
                    for transaction in orphaned_transactions:
                        transaction.user_id = admin_user.id
                    db.session.commit()
                    logger.info(f"Assigned {len(orphaned_transactions)} orphaned transactions to {admin_user.username}")
            
            logger.info("✅ Database repair completed successfully!")
            
            # Print summary
            total_users = User.query.count()
            total_items = Item.query.count()
            total_sales = Sale.query.count()
            
            print(f"\n📊 Database Summary:")
            print(f"   Users: {total_users}")
            print(f"   Items: {total_items}")
            print(f"   Sales: {total_sales}")
            
        except Exception as e:
            logger.error(f"Error during database repair: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    repair_database()
