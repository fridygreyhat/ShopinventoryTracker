
"""
Migration script to add multi-location inventory tables
Run this script to update your database with multi-location support
"""

from app import app, db
from models import Location, LocationStock, StockTransfer, StockTransferItem, Item, User

def migrate_database():
    """Create new tables and update existing ones for multi-location support"""
    
    with app.app_context():
        try:
            print("Creating multi-location tables...")
            
            # Create new tables
            db.create_all()
            
            # Add the track_by_location column to existing items table if it doesn't exist
            try:
                # Check if column exists first
                if 'postgresql' in app.config["SQLALCHEMY_DATABASE_URI"]:
                    # PostgreSQL syntax
                    result = db.session.execute(
                        db.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'item' AND column_name = 'track_by_location'")
                    ).fetchone()
                    column_exists = result is not None
                else:
                    # SQLite syntax
                    result = db.session.execute(db.text("PRAGMA table_info(item)"))
                    columns = [row[1] for row in result.fetchall()]
                    column_exists = 'track_by_location' in columns
                
                if not column_exists:
                    if 'postgresql' in app.config["SQLALCHEMY_DATABASE_URI"]:
                        db.session.execute(db.text('ALTER TABLE item ADD COLUMN track_by_location BOOLEAN DEFAULT FALSE'))
                    else:
                        db.session.execute(db.text('ALTER TABLE item ADD COLUMN track_by_location BOOLEAN DEFAULT 0'))
                    db.session.commit()
                    print("Added track_by_location column to items table")
                else:
                    print("Column track_by_location already exists")
            except Exception as e:
                print(f"Error adding track_by_location column: {e}")
            
            # Create a default location for existing users who don't have any
            users_without_locations = db.session.query(User).outerjoin(Location).filter(Location.id == None).all()
            
            for user in users_without_locations:
                default_location = Location(
                    name="Main Location",
                    code="MAIN",
                    type="warehouse",
                    is_default=True,
                    is_active=True,
                    user_id=user.id
                )
                db.session.add(default_location)
                print(f"Created default location for user: {user.username}")
            
            db.session.commit()
            print("Multi-location database migration completed successfully!")
            print("\nNew features available:")
            print("- Multi-location inventory tracking")
            print("- Stock transfers between locations")
            print("- Location-specific reporting")
            print("- Stock level management per location")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_database()
