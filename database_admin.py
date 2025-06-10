
#!/usr/bin/env python3
"""
Simple database admin interface
"""

from app import app, db
from models import *
from sqlalchemy import text
import json

class DatabaseAdmin:
    def __init__(self):
        self.app = app
        
    def list_tables(self):
        """List all database tables"""
        with app.app_context():
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print("Available tables:")
            for i, table in enumerate(sorted(tables), 1):
                print(f"{i:2d}. {table}")
            return tables
    
    def describe_table(self, table_name):
        """Describe table structure"""
        with app.app_context():
            try:
                inspector = db.inspect(db.engine)
                columns = inspector.get_columns(table_name)
                
                print(f"\nTable: {table_name}")
                print("-" * 50)
                print(f"{'Column':<20} {'Type':<20} {'Nullable':<10}")
                print("-" * 50)
                
                for col in columns:
                    nullable = "YES" if col['nullable'] else "NO"
                    print(f"{col['name']:<20} {str(col['type']):<20} {nullable:<10}")
                    
            except Exception as e:
                print(f"Error describing table: {e}")
    
    def query_table(self, table_name, limit=10):
        """Query table data"""
        with app.app_context():
            try:
                query = f"SELECT * FROM {table_name} LIMIT {limit}"
                result = db.session.execute(text(query))
                rows = result.fetchall()
                
                if rows:
                    # Get column names
                    columns = list(rows[0]._mapping.keys())
                    
                    print(f"\nData from {table_name} (showing {len(rows)} rows):")
                    print("-" * 80)
                    
                    # Print header
                    header = " | ".join(f"{col[:15]:<15}" for col in columns)
                    print(header)
                    print("-" * 80)
                    
                    # Print rows
                    for row in rows:
                        row_data = " | ".join(f"{str(val)[:15]:<15}" for val in row._mapping.values())
                        print(row_data)
                else:
                    print(f"No data found in {table_name}")
                    
            except Exception as e:
                print(f"Error querying table: {e}")
    
    def backup_database(self):
        """Create a backup of the database"""
        with app.app_context():
            try:
                backup_data = {}
                
                # Backup users
                backup_data['users'] = [user.to_dict() for user in User.query.all()]
                
                # Backup items
                backup_data['items'] = [item.to_dict() for item in Item.query.all()]
                
                # Backup sales
                backup_data['sales'] = [sale.to_dict() for sale in Sale.query.all()]
                
                # Backup settings
                backup_data['settings'] = [setting.to_dict() for setting in Setting.query.all()]
                
                # Save to file
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"database_backup_{timestamp}.json"
                
                with open(filename, 'w') as f:
                    json.dump(backup_data, f, indent=2, default=str)
                
                print(f"Database backup created: {filename}")
                
            except Exception as e:
                print(f"Error creating backup: {e}")
    
    def interactive_shell(self):
        """Start interactive database shell"""
        print("Database Admin Shell")
        print("Commands: tables, describe <table>, query <table> [limit], backup, exit")
        
        while True:
            try:
                command = input("\ndb> ").strip().split()
                
                if not command:
                    continue
                    
                if command[0] == "exit":
                    break
                elif command[0] == "tables":
                    self.list_tables()
                elif command[0] == "describe" and len(command) > 1:
                    self.describe_table(command[1])
                elif command[0] == "query" and len(command) > 1:
                    limit = int(command[2]) if len(command) > 2 else 10
                    self.query_table(command[1], limit)
                elif command[0] == "backup":
                    self.backup_database()
                else:
                    print("Unknown command. Use: tables, describe <table>, query <table> [limit], backup, exit")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    admin = DatabaseAdmin()
    admin.interactive_shell()
