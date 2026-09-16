import os
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

class Issue:
    def __init__(self, mongo):
        self.mongo = mongo
        db_name = os.getenv('MONGO_DB_NAME', 'smart_campus')
        if hasattr(mongo, 'db') and mongo.db is not None:
            self.collection = mongo.db['issues']
        elif hasattr(mongo, 'cx') and mongo.cx is not None:
            self.collection = mongo.cx[db_name]['issues']
        else:
            self.collection = mongo['issues']

    def create_issue(self, facility, title, description, reporter_name, reporter_email, image_url=None):
        """Create a new issue report with optional image attachment"""
        issue = {
            'facility': facility,
            'title': title,
            'description': description,
            'reporter_name': reporter_name,
            'reporter_email': reporter_email,
            'image_url': image_url,
            'status': 'pending',  # pending, in_progress, resolved, rejected
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = self.collection.insert_one(issue)
        return result.inserted_id
    
    def get_all_issues(self, limit=100, skip=0, status=None, facility=None, search=None):
        """Get issues sorted by date with optional filtering and search"""
        import re
        query = {}
        if status:
            query['status'] = status
        if facility:
            query['facility'] = facility
        if search:
            escaped = re.escape(search.strip())
            regex = re.compile(escaped, re.IGNORECASE)
            query['$or'] = [
                {'title': regex},
                {'description': regex},
                {'reporter_name': regex},
                {'reporter_email': regex},
                {'facility': regex}
            ]

        return list(self.collection.find(query).sort('created_at', -1).skip(skip).limit(limit))

    def count_filtered_issues(self, status=None, facility=None, search=None):
        """Count issues matching criteria for pagination"""
        import re
        query = {}
        if status:
            query['status'] = status
        if facility:
            query['facility'] = facility
        if search:
            escaped = re.escape(search.strip())
            regex = re.compile(escaped, re.IGNORECASE)
            query['$or'] = [
                {'title': regex},
                {'description': regex},
                {'reporter_name': regex},
                {'reporter_email': regex},
                {'facility': regex}
            ]

        return self.collection.count_documents(query)
    
    def get_issue_by_id(self, issue_id):
        """Get issue by ID"""
        try:
            return self.collection.find_one({'_id': ObjectId(issue_id)})
        except (InvalidId, TypeError):
            return None
    
    def update_issue_status(self, issue_id, status):
        """Update issue status"""
        try:
            result = self.collection.update_one(
                {'_id': ObjectId(issue_id)},
                {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
            )
            return result.modified_count > 0
        except (InvalidId, TypeError):
            return False
    
    def get_issues_by_facility(self, facility):
        """Get issues for a specific facility"""
        return list(self.collection.find({'facility': facility}).sort('created_at', -1))

    def get_issues_by_email(self, email):
        """Get all issues reported by a given email address"""
        return list(self.collection.find({'reporter_email': email}).sort('created_at', -1))
    
    def get_pending_issues(self):
        """Get all pending issues"""
        return list(self.collection.find({'status': 'pending'}).sort('created_at', -1))
    
    def get_issue_stats(self):
        """Get issue statistics"""
        pipeline = [
            {'$group': {
                '_id': '$status',
                'count': {'$sum': 1}
            }}
        ]
        stats = list(self.collection.aggregate(pipeline))
        
        result = {
            'pending': 0,
            'in_progress': 0,
            'resolved': 0,
            'rejected': 0
        }
        
        for stat in stats:
            result[stat['_id']] = stat['count']
        
        result['total'] = self.collection.count_documents({})
        return result