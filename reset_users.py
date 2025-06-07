
#!/usr/bin/env python3
"""
Script to reset and remove all registered users from the database
This will also remove all associated data (items, sales, transactions, etc.)
"""

from app import app, db
from models import (
    User, Item, Sale, SaleItem, FinancialTransaction, 
    OnDemandProduct, Setting, Subuser, SubuserPermission,
    LayawayPlan, LayawayPayment, Location, LocationStock,
    StockTransfer, StockTransferItem, Category, Subcategory,
    ChartOfAccounts, Journal, JournalEntry, GeneralLedger,
    CashFlow, BalanceSheet, BankAccount, BankTransfer,
    BankReconciliation, BranchEquity, PricingRule, FinancialSummary
)
from sqlalchemy import text
import sys

def confirm_reset():
    """Confirm with user before proceeding"""
    print("⚠️  WARNING: This will permanently delete ALL users and their data!")
    print("This includes:")
    print("- All user accounts")
    print("- All inventory items") 
    print("- All sales records")
    print("- All financial transactions")
    print("- All locations and stock data")
    print("- All settings and configurations")
    print("- ALL associated data")
    print()
    
    response = input("Are you sure you want to proceed? Type 'DELETE ALL USERS' to confirm: ")
    return response == "DELETE ALL USERS"

def backup_before_reset():
    """Create a backup before reset"""
    try:
        import json
        from datetime import datetime
        
        backup_data = {}
        
        with app.app_context():
            # Count records before backup
            user_count = User.query.count()
            item_count = Item.query.count()
            sale_count = Sale.query.count()
            
            print(f"📊 Current database state:")
            print(f"   - Users: {user_count}")
            print(f"   - Items: {item_count}")
            print(f"   - Sales: {sale_count}")
            
            if user_count == 0:
                print("ℹ️  No users found in database")
                return None
            
            print("💾 Creating backup before reset...")
            
            # Backup users
            backup_data['users'] = [user.to_dict() for user in User.query.all()]
            
            # Backup items  
            backup_data['items'] = [item.to_dict() for item in Item.query.all()]
            
            # Backup sales
            backup_data['sales'] = [sale.to_dict() for sale in Sale.query.all()]
            
            # Save backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"user_reset_backup_{timestamp}.json"
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            print(f"✅ Backup saved as: {backup_file}")
            return backup_file
            
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        print("Continuing without backup...")
        return None

def reset_all_users():
    """Reset and remove all users and their data"""
    with app.app_context():
        try:
            print("🗑️  Starting user reset process...")
            
            # Get initial counts
            initial_users = User.query.count()
            
            if initial_users == 0:
                print("ℹ️  No users found to delete")
                return True
            
            # Delete in proper order to avoid foreign key constraints
            print("🔄 Deleting user-related data...")
            
            # Delete journal entries and accounting data
            db.session.execute(text("DELETE FROM journal_entry"))
            db.session.execute(text("DELETE FROM general_ledger"))
            db.session.execute(text("DELETE FROM journal"))
            db.session.execute(text("DELETE FROM chart_of_accounts"))
            
            # Delete bank and financial data
            db.session.execute(text("DELETE FROM bank_reconciliation"))
            db.session.execute(text("DELETE FROM bank_transfer"))
            db.session.execute(text("DELETE FROM bank_account"))
            db.session.execute(text("DELETE FROM cash_flow"))
            db.session.execute(text("DELETE FROM balance_sheet"))
            db.session.execute(text("DELETE FROM branch_equity"))
            
            # Delete layaway data
            db.session.execute(text("DELETE FROM layaway_payment"))
            db.session.execute(text("DELETE FROM layaway_plan"))
            
            # Delete stock transfer data
            db.session.execute(text("DELETE FROM stock_transfer_item"))
            db.session.execute(text("DELETE FROM stock_transfer"))
            
            # Delete location and stock data
            db.session.execute(text("DELETE FROM location_stock"))
            db.session.execute(text("DELETE FROM location"))
            
            # Delete sales data
            db.session.execute(text("DELETE FROM sale_item"))
            db.session.execute(text("DELETE FROM sale"))
            
            # Delete financial transactions
            db.session.execute(text("DELETE FROM financial_transaction"))
            db.session.execute(text("DELETE FROM financial_summary"))
            
            # Delete inventory and products
            db.session.execute(text("DELETE FROM item"))
            db.session.execute(text("DELETE FROM on_demand_product"))
            db.session.execute(text("DELETE FROM pricing_rule"))
            
            # Delete categories
            db.session.execute(text("DELETE FROM subcategory"))
            db.session.execute(text("DELETE FROM category"))
            
            # Delete subuser data
            db.session.execute(text("DELETE FROM subuser_permission"))
            db.session.execute(text("DELETE FROM subuser"))
            
            # Delete settings (optional - you might want to keep some)
            db.session.execute(text("DELETE FROM setting"))
            
            # Finally delete users
            db.session.execute(text("DELETE FROM user"))
            
            # Commit all deletions
            db.session.commit()
            
            # Verify deletion
            remaining_users = User.query.count()
            remaining_items = Item.query.count()
            remaining_sales = Sale.query.count()
            
            print(f"✅ Reset completed!")
            print(f"   - Deleted {initial_users} users")
            print(f"   - Remaining users: {remaining_users}")
            print(f"   - Remaining items: {remaining_items}")
            print(f"   - Remaining sales: {remaining_sales}")
            
            if remaining_users == 0:
                print("🎉 All users and their data have been successfully removed!")
                return True
            else:
                print(f"⚠️  Warning: {remaining_users} users still remain")
                return False
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during reset: {e}")
            return False

def reset_database_sequences():
    """Reset database auto-increment sequences"""
    with app.app_context():
        try:
            print("🔄 Resetting database sequences...")
            
            # Reset PostgreSQL sequences for auto-increment IDs
            tables_with_ids = [
                'user', 'item', 'sale', 'sale_item', 'financial_transaction',
                'on_demand_product', 'setting', 'subuser', 'subuser_permission',
                'layaway_plan', 'layaway_payment', 'location', 'location_stock',
                'stock_transfer', 'stock_transfer_item', 'category', 'subcategory',
                'chart_of_accounts', 'journal', 'journal_entry', 'general_ledger',
                'cash_flow', 'balance_sheet', 'bank_account', 'bank_transfer',
                'bank_reconciliation', 'branch_equity', 'pricing_rule', 'financial_summary'
            ]
            
            for table in tables_with_ids:
                try:
                    db.session.execute(text(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1"))
                except Exception:
                    # Some tables might not have sequences
                    pass
            
            db.session.commit()
            print("✅ Database sequences reset")
            
        except Exception as e:
            print(f"⚠️  Could not reset sequences: {e}")

def main():
    """Main reset function"""
    print("🔄 User Reset Tool")
    print("=" * 50)
    
    # Confirm action
    if not confirm_reset():
        print("❌ Reset cancelled by user")
        return
    
    # Create backup
    backup_file = backup_before_reset()
    
    # Perform reset
    if reset_all_users():
        reset_database_sequences()
        print("\n🎉 User reset completed successfully!")
        print("\nNext steps:")
        print("1. You can now register new users")
        print("2. The database is clean and ready for fresh data")
        if backup_file:
            print(f"3. Your data backup is saved as: {backup_file}")
    else:
        print("\n❌ Reset failed. Please check the errors above.")
        if backup_file:
            print(f"Your data backup is still available: {backup_file}")

if __name__ == "__main__":
    main()
