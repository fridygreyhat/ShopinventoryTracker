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
        print(f"❌ Error creating backup: {str(e)}")
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

            # Delete stock and location data
            db.session.execute(text("DELETE FROM stock_transfer_item"))
            db.session.execute(text("DELETE FROM stock_transfer"))
            db.session.execute(text("DELETE FROM location_stock"))
            db.session.execute(text("DELETE FROM location"))

            # Delete sales data
            db.session.execute(text("DELETE FROM sale_item"))
            db.session.execute(text("DELETE FROM sale"))

            # Delete inventory and product data
            db.session.execute(text("DELETE FROM item"))
            db.session.execute(text("DELETE FROM on_demand_product"))

            # Delete financial transactions
            db.session.execute(text("DELETE FROM financial_transaction"))
            db.session.execute(text("DELETE FROM financial_summary"))

            # Delete categories (but keep them as they might be reusable)
            # db.session.execute(text("DELETE FROM subcategory"))
            # db.session.execute(text("DELETE FROM category"))

            # Delete pricing rules
            db.session.execute(text("DELETE FROM pricing_rule"))

            # Delete subusers and permissions
            db.session.execute(text("DELETE FROM subuser_permission"))
            db.session.execute(text("DELETE FROM subuser"))

            # Delete user-specific settings (but keep global ones)
            db.session.execute(text("DELETE FROM setting WHERE key LIKE 'user_%'"))

            # Finally delete users
            db.session.execute(text("DELETE FROM \"user\""))

            # Commit all deletions
            db.session.commit()

            # Verify deletion
            remaining_users = User.query.count()

            print(f"✅ Reset completed successfully!")
            print(f"   - Deleted {initial_users} users")
            print(f"   - Remaining users: {remaining_users}")

            if remaining_users == 0:
                print("🎉 All users successfully removed from database")
                return True
            else:
                print("⚠️  Some users may still remain")
                return False

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during reset: {str(e)}")
            return False

def main():
    """Main function"""
    print("🔧 User Reset Tool")
    print("=" * 50)

    # Check confirmation
    if not confirm_reset():
        print("❌ Reset cancelled by user")
        sys.exit(0)

    # Create backup
    backup_file = backup_before_reset()
    if backup_file:
        print(f"📁 Backup created: {backup_file}")

    # Proceed with reset
    print("\n🚀 Proceeding with user reset...")
    success = reset_all_users()

    if success:
        print("\n✅ User reset completed successfully!")
        print("💡 You can now register new users from the login page")
    else:
        print("\n❌ User reset failed!")
        if backup_file:
            print(f"💾 Your data backup is available at: {backup_file}")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()