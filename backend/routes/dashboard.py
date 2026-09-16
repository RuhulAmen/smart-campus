from flask import Blueprint, jsonify
from models import Facility, Announcement, Issue
from utils.helpers import token_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@token_required
def get_dashboard_stats(current_user):
    """Get dashboard statistics"""
    try:
        facility_model = Facility(dashboard_bp.mongo)
        announcement_model = Announcement(dashboard_bp.mongo)
        issue_model = Issue(dashboard_bp.mongo)
        
        facilities = facility_model.get_all_facilities()
        
        # Count facilities by status
        status_count = {
            'operational': 0,
            'maintenance': 0,
            'closed': 0
        }
        
        for facility in facilities:
            status = facility.get('status', 'operational')
            if status in status_count:
                status_count[status] += 1
        
        # Get stats
        stats = {
            'total_facilities': len(facilities),
            'operational_facilities': status_count['operational'],
            'maintenance_facilities': status_count['maintenance'],
            'closed_facilities': status_count['closed'],
            'total_announcements': announcement_model.collection.count_documents({'status': 'active'}),
            'total_issues': issue_model.collection.count_documents({}),
            'pending_issues': issue_model.collection.count_documents({'status': 'pending'}),
            'in_progress_issues': issue_model.collection.count_documents({'status': 'in_progress'}),
            'resolved_issues': issue_model.collection.count_documents({'status': 'resolved'}),
            'rejected_issues': issue_model.collection.count_documents({'status': 'rejected'}),
            'recent_announcements': announcement_model.get_recent_announcements(limit=3)
        }
        
        # Convert ObjectId to string for recent announcements
        for ann in stats['recent_announcements']:
            ann['_id'] = str(ann['_id'])
        
        return jsonify({'stats': stats}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500