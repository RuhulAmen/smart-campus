import os
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

class Announcement:
    def __init__(self, mongo):
        self.mongo = mongo
        db_name = os.getenv('MONGO_DB_NAME', 'smart_campus')
        if hasattr(mongo, 'db') and mongo.db is not None:
            self.collection = mongo.db['announcements']
        elif hasattr(mongo, 'cx') and mongo.cx is not None:
            self.collection = mongo.cx[db_name]['announcements']
        else:
            self.collection = mongo['announcements']
    
    def create_announcement(self, title, description, priority, category, created_by):
        """Create a new announcement"""
        announcement = {
            'title': title,
            'description': description,
            'priority': priority,  # high, medium, low
            'category': category,
            'created_by': created_by,
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'status': 'active'
        }
        
        result = self.collection.insert_one(announcement)
        return result.inserted_id
    
    def get_all_announcements(self, limit=100, skip=0, priority=None, category=None, search=None):
        """Get active announcements sorted by date with optional filtering and search"""
        import re
        query = {'status': 'active'}
        if priority:
            query['priority'] = priority
        if category:
            query['category'] = category
        if search:
            escaped = re.escape(search.strip())
            regex = re.compile(escaped, re.IGNORECASE)
            query['$or'] = [
                {'title': regex},
                {'description': regex},
                {'category': regex}
            ]
        return list(self.collection.find(query).sort('created_at', -1).skip(skip).limit(limit))

    def count_filtered_announcements(self, priority=None, category=None, search=None):
        """Count active announcements matching criteria"""
        import re
        query = {'status': 'active'}
        if priority:
            query['priority'] = priority
        if category:
            query['category'] = category
        if search:
            escaped = re.escape(search.strip())
            regex = re.compile(escaped, re.IGNORECASE)
            query['$or'] = [
                {'title': regex},
                {'description': regex},
                {'category': regex}
            ]
        return self.collection.count_documents(query)
    
    def get_announcement_by_id(self, announcement_id):
        """Get announcement by ID"""
        try:
            return self.collection.find_one({'_id': ObjectId(announcement_id), 'status': 'active'})
        except (InvalidId, TypeError):
            return None
    
    def update_announcement(self, announcement_id, update_data):
        """Update announcement"""
        try:
            update_data['updated_at'] = datetime.utcnow()
            result = self.collection.update_one(
                {'_id': ObjectId(announcement_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except (InvalidId, TypeError):
            return False
    
    def delete_announcement(self, announcement_id):
        """Soft delete an announcement"""
        try:
            result = self.collection.update_one(
                {'_id': ObjectId(announcement_id)},
                {'$set': {'status': 'inactive', 'updated_at': datetime.utcnow()}}
            )
            return result.modified_count > 0
        except (InvalidId, TypeError):
            return False
    
    def get_recent_announcements(self, limit=5):
        """Get recent announcements"""
        return list(self.collection.find(
            {'status': 'active'}
        ).sort('created_at', -1).limit(limit))
    
    def get_by_priority(self, priority, limit=50):
        """Get announcements by priority"""
        return list(self.collection.find(
            {'status': 'active', 'priority': priority}
        ).sort('created_at', -1).limit(limit))