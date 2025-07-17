
from firebase_config import firebase_config
from firebase_adapter import firebase_adapter
import logging

logger = logging.getLogger(__name__)

def get_database_type():
    """Determine which database system to use"""
    if firebase_config.initialized:
        return 'firebase'
    else:
        return 'postgresql'

def is_firebase_available():
    """Check if Firebase is available and initialized"""
    return firebase_config.initialized

class DatabaseManager:
    """Manager class to handle operations across different database systems"""
    
    @staticmethod
    def get_user_items(user_id, **kwargs):
        """Get user items from available database"""
        if is_firebase_available():
            return firebase_adapter.get_items_by_user(user_id, **kwargs)
        else:
            # PostgreSQL fallback
            from models import Item
            query = Item.query.filter(Item.user_id == user_id, Item.is_active == True)
            # Apply filters as needed for PostgreSQL
            return [item.to_dict() for item in query.all()]
    
    @staticmethod
    def create_user_item(item_data, user_id):
        """Create item in available database"""
        if is_firebase_available():
            return firebase_adapter.create_item(item_data, user_id)
        else:
            # PostgreSQL fallback
            from models import Item
            from extensions import db
            item = Item(**item_data)
            item.user_id = user_id
            db.session.add(item)
            db.session.commit()
            return item

# Global database manager instance
db_manager = DatabaseManager()
