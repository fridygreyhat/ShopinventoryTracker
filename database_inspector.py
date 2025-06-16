
#!/usr/bin/env python3
"""
Database inspection and access script
"""

from app import app, db
from models import User, Item, Sale, FinancialTransaction, Setting
from sqlalchemy import text

def inspect_database():
    """Inspect database structure and data"""
    with app.app_context():
        try:
            print("=== DATABASE INSPECTION ===")
            print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            print()
            
            # Check tables
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Available Tables ({len(tables)}):")
            for table in sorted(tables):
                print(f"  - {table}")
            print()
            
            # Check users
            users = User.query.all()
            print(f"Users in database: {len(users)}")
            for user in users:
                print(f"  - {user.username} ({user.email}) - Admin: {user.is_admin}")
            print()
            
            # Check items
            items = Item.query.all()
            print(f"Inventory items: {len(items)}")
            for item in items[:5]:  # Show first 5
                print(f"  - {item.name} (Qty: {item.quantity}, Price: {item.selling_price_retail})")
            if len(items) > 5:
                print(f"  ... and {len(items) - 5} more items")
            print()
            
            # Check sales
            sales = Sale.query.all()
            print(f"Sales records: {len(sales)}")
            total_sales = sum(sale.total for sale in sales)
            print(f"Total sales value: {total_sales}")
            print()
            
            # Check financial transactions
            transactions = FinancialTransaction.query.all()
            print(f"Financial transactions: {len(transactions)}")
            total_income = sum(t.amount for t in transactions if t.transaction_type == 'Income')
            total_expenses = sum(t.amount for t in transactions if t.transaction_type == 'Expense')
            print(f"Total income: {total_income}")
            print(f"Total expenses: {total_expenses}")
            print(f"Net profit: {total_income - total_expenses}")
            
        except Exception as e:
            print(f"Error inspecting database: {str(e)}")

def run_custom_query(query_sql):
    """Run a custom SQL query"""
    with app.app_context():
        try:
            result = db.session.execute(text(query_sql))
            rows = result.fetchall()
            
            print(f"Query: {query_sql}")
            print(f"Results ({len(rows)} rows):")
            for row in rows:
                print(f"  {dict(row._mapping)}")
                
        except Exception as e:
            print(f"Error executing query: {str(e)}")

def export_data_to_json():
    """Export database data to JSON files"""
    import json
    from datetime import datetime
    
    with app.app_context():
        try:
            # Export users
            users = [user.to_dict() for user in User.query.all()]
            with open('export_users.json', 'w') as f:
                json.dump(users, f, indent=2, default=str)
            
            # Export items
            items = [item.to_dict() for item in Item.query.all()]
            with open('export_items.json', 'w') as f:
                json.dump(items, f, indent=2, default=str)
            
            # Export sales
            sales = [sale.to_dict() for sale in Sale.query.all()]
            with open('export_sales.json', 'w') as f:
                json.dump(sales, f, indent=2, default=str)
            
            print("Data exported to JSON files:")
            print("  - export_users.json")
            print("  - export_items.json") 
            print("  - export_sales.json")
            
        except Exception as e:
            print(f"Error exporting data: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "export":
            export_data_to_json()
        elif sys.argv[1] == "query" and len(sys.argv) > 2:
            run_custom_query(" ".join(sys.argv[2:]))
        else:
            print("Usage:")
            print("  python database_inspector.py - Inspect database")
            print("  python database_inspector.py export - Export data to JSON")
            print("  python database_inspector.py query 'SELECT * FROM user' - Run custom query")
    else:
        inspect_database()
