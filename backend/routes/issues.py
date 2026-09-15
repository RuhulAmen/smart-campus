from flask import Blueprint, request, jsonify
from models import Issue, Announcement
from utils.helpers import token_required, admin_required
from utils.limiter import limiter
import re

issues_bp = Blueprint('issues', __name__)

EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'

# NOTE: static/special paths ('/stats', '/facility/...', '/track') are declared
# BEFORE '/<issue_id>' so Flask does not capture them as an issue ID.


# strict_slashes=False: the SPA calls these without a trailing slash, so without
# it every request gets an extra 308 redirect (and breaks cross-origin POSTs).
@issues_bp.route('/', methods=['GET'], strict_slashes=False)
def get_issues():
    """Get all issues"""
    try:
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))

        issue_model = Issue(issues_bp.mongo)
        issues = issue_model.get_all_issues(limit=limit, skip=skip)

        for issue in issues:
            issue['_id'] = str(issue['_id'])

        return jsonify({'issues': issues}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/', methods=['POST'], strict_slashes=False)
@limiter.limit("10 per hour")
def create_issue():
    """Create a new issue report (Public)"""
    try:
        data = request.get_json(silent=True) or {}

        required_fields = ['facility', 'title', 'description', 'reporter_name', 'reporter_email']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        title = str(data['title']).strip()
        description = str(data['description']).strip()
        reporter_name = str(data['reporter_name']).strip()
        reporter_email = str(data['reporter_email']).strip()

        if not title or not description or not reporter_name:
            return jsonify({'error': 'All fields are required'}), 400

        if not re.match(EMAIL_REGEX, reporter_email):
            return jsonify({'error': 'Please enter a valid email address'}), 400

        issue_model = Issue(issues_bp.mongo)
        issue_id = issue_model.create_issue(
            facility=data['facility'],
            title=title,
            description=description,
            reporter_name=reporter_name,
            reporter_email=reporter_email
        )

        issue = issue_model.get_issue_by_id(issue_id)
        issue['_id'] = str(issue['_id'])

        # Create an announcement for this issue
        announcement_model = Announcement(issues_bp.mongo)
        announcement_model.create_announcement(
            title=f"Issue Reported: {title}",
            description=f"{reporter_name} reported an issue with {data['facility']}: {description}",
            priority='medium',
            category='Issue Report',
            created_by='system'
        )

        return jsonify({
            'message': 'Issue reported successfully',
            'issue': issue
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/stats', methods=['GET'])
def get_issue_stats():
    """Get issue statistics"""
    try:
        issue_model = Issue(issues_bp.mongo)
        stats = issue_model.get_issue_stats()
        return jsonify({'stats': stats}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/facility/<facility_name>', methods=['GET'])
def get_issues_by_facility(facility_name):
    """Get issues for a specific facility"""
    try:
        issue_model = Issue(issues_bp.mongo)
        issues = issue_model.get_issues_by_facility(facility_name)

        for issue in issues:
            issue['_id'] = str(issue['_id'])

        return jsonify({'issues': issues}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/track', methods=['GET'])
def get_tracked_issues():
    """Get issues reported by a given email (for the 'My Reports' page)"""
    try:
        email = (request.args.get('email') or '').strip()

        if not email or not re.match(EMAIL_REGEX, email):
            return jsonify({'error': 'A valid email is required'}), 400

        issue_model = Issue(issues_bp.mongo)
        issues = issue_model.get_issues_by_email(email)

        for issue in issues:
            issue['_id'] = str(issue['_id'])

        return jsonify({'issues': issues}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/<issue_id>', methods=['GET'])
def get_issue(issue_id):
    """Get a specific issue"""
    try:
        issue_model = Issue(issues_bp.mongo)
        issue = issue_model.get_issue_by_id(issue_id)

        if not issue:
            return jsonify({'error': 'Issue not found'}), 404

        issue['_id'] = str(issue['_id'])
        return jsonify({'issue': issue}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/<issue_id>/status', methods=['PATCH'])
@token_required
@admin_required
def update_issue_status(current_user, issue_id):
    """Update issue status (Admin only)"""
    try:
        data = request.get_json(silent=True) or {}

        if not data.get('status'):
            return jsonify({'error': 'Status is required'}), 400

        valid_statuses = ['pending', 'in_progress', 'resolved', 'rejected']
        if data['status'] not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400

        issue_model = Issue(issues_bp.mongo)

        # Check if issue exists
        issue = issue_model.get_issue_by_id(issue_id)
        if not issue:
            return jsonify({'error': 'Issue not found'}), 404

        # Update status
        issue_model.update_issue_status(issue_id, data['status'])

        # Create announcement for status update
        if data['status'] in ['resolved', 'rejected']:
            announcement_model = Announcement(issues_bp.mongo)
            status_msg = 'resolved' if data['status'] == 'resolved' else 'reviewed and rejected'
            announcement_model.create_announcement(
                title=f"Issue {status_msg}: {issue['title']}",
                description=f"The issue reported by {issue['reporter_name']} has been {status_msg}.",
                priority='low',
                category='Issue Update',
                created_by=current_user['_id']
            )

        return jsonify({
            'message': 'Issue status updated successfully',
            'status': data['status']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
