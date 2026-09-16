"""Admin user management and data export routes."""
import math
import re
import io
import csv
from flask import Blueprint, request, jsonify, Response
from models import User, Issue, Facility
from utils.helpers import token_required, admin_required
from utils.validation import validate_request
from schemas import UserRoleUpdateSchema, UserStatusUpdateSchema

admin_bp = Blueprint('admin', __name__)


def _sanitize_user(user):
    """Strip password hash and stringify ObjectId."""
    if not user:
        return None
    doc = dict(user)
    doc.pop('password', None)
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    if 'created_at' in doc and hasattr(doc['created_at'], 'isoformat'):
        doc['created_at'] = doc['created_at'].isoformat()
    if 'updated_at' in doc and hasattr(doc['updated_at'], 'isoformat'):
        doc['updated_at'] = doc['updated_at'].isoformat()
    return doc


@admin_bp.route('/users', methods=['GET'], strict_slashes=False)
@token_required
@admin_required
def get_users(current_user):
    """List registered users with pagination, role filtering, and search."""
    try:
        page = max(1, int(request.args.get('page', 1)))
        limit = min(100, max(1, int(request.args.get('limit', 20))))
        search = (request.args.get('search') or '').strip()
        role = (request.args.get('role') or '').strip().lower()
        status = (request.args.get('status') or '').strip().lower()

        query = {}
        if role in ('student', 'admin'):
            query['role'] = role

        if status == 'active':
            query['is_active'] = True
        elif status in ('inactive', 'disabled'):
            query['is_active'] = False

        if search:
            escaped = re.escape(search)
            regex = re.compile(escaped, re.IGNORECASE)
            query['$or'] = [
                {'full_name': regex},
                {'email': regex},
                {'student_id': regex}
            ]

        user_model = User(admin_bp.mongo)
        total = user_model.collection.count_documents(query)
        pages = max(1, math.ceil(total / limit)) if total > 0 else 1
        skip = (page - 1) * limit

        cursor = user_model.collection.find(query).sort('created_at', -1).skip(skip).limit(limit)
        users = [_sanitize_user(u) for u in cursor]

        return jsonify({
            'users': users,
            'total': total,
            'page': page,
            'pages': pages,
            'limit': limit
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/<user_id>/role', methods=['PATCH'])
@token_required
@admin_required
def update_user_role(current_user, user_id):
    """Change user role (promote to admin or demote to student)."""
    try:
        data, error = validate_request(UserRoleUpdateSchema)
        if error:
            return error

        new_role = data['role']

        # Prevent an admin from accidentally demoting themselves
        if str(current_user.get('_id')) == str(user_id) and new_role != 'admin':
            return jsonify({'error': 'You cannot revoke your own administrator privileges'}), 400

        user_model = User(admin_bp.mongo)
        user = user_model.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        success = user_model.update_user(user_id, {'role': new_role})
        if not success:
            return jsonify({'error': 'Could not update user role'}), 500

        return jsonify({
            'message': f"User role successfully updated to {new_role}",
            'user_id': str(user_id),
            'role': new_role
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/<user_id>/status', methods=['PATCH'])
@token_required
@admin_required
def update_user_status(current_user, user_id):
    """Activate or deactivate a user account."""
    try:
        data, error = validate_request(UserStatusUpdateSchema)
        if error:
            return error

        is_active = data['is_active']

        # Prevent an admin from disabling their own account
        if str(current_user.get('_id')) == str(user_id) and not is_active:
            return jsonify({'error': 'You cannot deactivate your own account'}), 400

        user_model = User(admin_bp.mongo)
        user = user_model.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        success = user_model.update_user(user_id, {'is_active': is_active})
        if not success:
            return jsonify({'error': 'Could not update user status'}), 500

        status_str = 'activated' if is_active else 'deactivated'
        return jsonify({
            'message': f"User account has been {status_str}",
            'user_id': str(user_id),
            'is_active': is_active
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, user_id):
    """Delete a user account."""
    try:
        # Prevent self deletion
        if str(current_user.get('_id')) == str(user_id):
            return jsonify({'error': 'You cannot delete your own account'}), 400

        user_model = User(admin_bp.mongo)
        user = user_model.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        success = user_model.delete_user(user_id)
        if not success:
            return jsonify({'error': 'Could not delete user'}), 500

        return jsonify({'message': 'User deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/export/issues.csv', methods=['GET'])
@token_required
@admin_required
def export_issues_csv(current_user):
    """Export all reported campus issues to a CSV spreadsheet."""
    try:
        issue_model = Issue(admin_bp.mongo)
        issues = issue_model.get_all_issues(limit=5000, skip=0)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Issue ID', 'Facility', 'Title', 'Description', 'Status',
            'Reporter Name', 'Reporter Email', 'Photo Attached', 'Reported Date'
        ])

        for issue in issues:
            writer.writerow([
                str(issue.get('_id', '')),
                issue.get('facility', ''),
                issue.get('title', ''),
                (issue.get('description') or '').replace('\n', ' '),
                issue.get('status', ''),
                issue.get('reporter_name', ''),
                issue.get('reporter_email', ''),
                'Yes' if issue.get('image_url') else 'No',
                str(issue.get('date', ''))
            ])

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=smart_campus_issues.csv"}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/export/facilities.csv', methods=['GET'])
@token_required
@admin_required
def export_facilities_csv(current_user):
    """Export all campus facilities to a CSV spreadsheet."""
    try:
        fac_model = Facility(admin_bp.mongo)
        facilities = fac_model.get_all_facilities()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Facility ID', 'Name', 'Location', 'Status', 'Description'])

        for fac in facilities:
            writer.writerow([
                str(fac.get('_id', '')),
                fac.get('name', ''),
                fac.get('location', ''),
                fac.get('status', ''),
                (fac.get('description') or '').replace('\n', ' ')
            ])

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=smart_campus_facilities.csv"}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

