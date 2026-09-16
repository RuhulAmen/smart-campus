from flask import Blueprint, request, jsonify
from models import Announcement
from utils.helpers import token_required, admin_required
from utils.validation import validate_request
from schemas import AnnouncementCreateSchema, AnnouncementUpdateSchema

announcements_bp = Blueprint('announcements', __name__)

# strict_slashes=False: the SPA calls these without a trailing slash, so without
# it every request gets an extra 308 redirect (and breaks cross-origin POSTs).
@announcements_bp.route('/', methods=['GET'], strict_slashes=False)
def get_announcements():
    """Get all announcements"""
    try:
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))
        
        announcement_model = Announcement(announcements_bp.mongo)
        announcements = announcement_model.get_all_announcements(limit=limit, skip=skip)
        
        # Convert ObjectId to string
        for announcement in announcements:
            announcement['_id'] = str(announcement['_id'])
        
        return jsonify({'announcements': announcements}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@announcements_bp.route('/recent', methods=['GET'])
def get_recent_announcements():
    """Get recent announcements for dashboard"""
    try:
        limit = int(request.args.get('limit', 5))
        
        announcement_model = Announcement(announcements_bp.mongo)
        announcements = announcement_model.get_recent_announcements(limit=limit)
        
        for announcement in announcements:
            announcement['_id'] = str(announcement['_id'])
        
        return jsonify({'announcements': announcements}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@announcements_bp.route('/priority/<priority>', methods=['GET'])
def get_announcements_by_priority(priority):
    """Get announcements by priority"""
    try:
        if priority not in ['high', 'medium', 'low']:
            return jsonify({'error': 'Invalid priority'}), 400
        
        announcement_model = Announcement(announcements_bp.mongo)
        announcements = announcement_model.get_by_priority(priority)
        
        for announcement in announcements:
            announcement['_id'] = str(announcement['_id'])
        
        return jsonify({'announcements': announcements}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@announcements_bp.route('/', methods=['POST'], strict_slashes=False)
@token_required
@admin_required
def create_announcement(current_user):
    """Create announcement (Admin only)"""
    try:
        data, error = validate_request(AnnouncementCreateSchema)
        if error:
            return error
        
        announcement_model = Announcement(announcements_bp.mongo)
        announcement_id = announcement_model.create_announcement(
            title=data['title'],
            description=data['description'],
            priority=data['priority'],
            category=data['category'],
            created_by=current_user['_id']
        )
        
        announcement = announcement_model.get_announcement_by_id(announcement_id)
        announcement['_id'] = str(announcement['_id'])
        
        return jsonify({
            'message': 'Announcement created successfully',
            'announcement': announcement
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@announcements_bp.route('/<announcement_id>', methods=['PUT'])
@token_required
@admin_required
def update_announcement(current_user, announcement_id):
    """Update announcement (Admin only)"""
    try:
        data, error = validate_request(AnnouncementUpdateSchema)
        if error:
            return error
        announcement_model = Announcement(announcements_bp.mongo)
        
        # Check if announcement exists
        announcement = announcement_model.get_announcement_by_id(announcement_id)
        if not announcement:
            return jsonify({'error': 'Announcement not found'}), 404
        
        # Schema already strips unknown fields; use validated data directly
        update_data = {k: v for k, v in data.items() if v is not None}
        
        if update_data:
            announcement_model.update_announcement(announcement_id, update_data)
        
        # Get updated announcement
        updated_announcement = announcement_model.get_announcement_by_id(announcement_id)
        updated_announcement['_id'] = str(updated_announcement['_id'])
        
        return jsonify({
            'message': 'Announcement updated successfully',
            'announcement': updated_announcement
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@announcements_bp.route('/<announcement_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_announcement(current_user, announcement_id):
    """Delete announcement (Admin only)"""
    try:
        announcement_model = Announcement(announcements_bp.mongo)
        
        # Check if announcement exists
        announcement = announcement_model.get_announcement_by_id(announcement_id)
        if not announcement:
            return jsonify({'error': 'Announcement not found'}), 404
        
        announcement_model.delete_announcement(announcement_id)
        
        return jsonify({'message': 'Announcement deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500