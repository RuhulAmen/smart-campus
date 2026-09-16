"""Unit and integration tests for Issues endpoints."""
import json
from unittest.mock import patch
from tests.test_base import BaseTestCase


class TestIssues(BaseTestCase):
    """Tests for /api/issues routes."""

    @patch('routes.issues.Issue')
    def test_get_issues_paginated(self, MockIssue):
        """Test retrieving issues with pagination and search parameters."""
        mock_instance = MockIssue.return_value
        mock_instance.get_all_issues.return_value = [
            {
                '_id': 'iss1',
                'title': 'Leaking Tap',
                'facility': 'Restroom 2F',
                'status': 'pending',
                'reporter_name': 'Alice',
                'reporter_email': 'alice@campus.edu'
            }
        ]
        mock_instance.count_filtered_issues.return_value = 1

        response = self.client.get('/api/issues/?page=1&limit=10&status=pending')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('issues', data)
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['page'], 1)
        self.assertEqual(len(data['issues']), 1)

    @patch('routes.issues.Announcement')
    @patch('routes.issues.notify_issue_reported')
    @patch('routes.issues.Issue')
    def test_create_issue_success(self, MockIssue, MockEmail, MockAnnouncement):
        """Test creating an issue with valid fields and photo attachment."""
        MockIssue.return_value.create_issue.return_value = 'iss_123'
        MockIssue.return_value.get_issue_by_id.return_value = {
            '_id': 'iss_123',
            'facility': 'Library',
            'title': 'Flickering lights in study hall',
            'description': 'Light tubes above desk 12 are blinking rapidly.',
            'reporter_name': 'Bob Student',
            'reporter_email': 'bob@campus.edu',
            'image_url': '/uploads/photo-123.jpg',
            'status': 'pending'
        }

        payload = {
            'facility': 'Library',
            'title': 'Flickering lights in study hall',
            'description': 'Light tubes above desk 12 are blinking rapidly.',
            'reporter_name': 'Bob Student',
            'reporter_email': 'bob@campus.edu',
            'image_url': '/uploads/photo-123.jpg'
        }

        response = self.client.post(
            '/api/issues/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('issue', data)
        self.assertEqual(data['issue']['_id'], 'iss_123')
        # Verify notification attempt
        MockEmail.assert_called_once()

    def test_create_issue_missing_required_fields(self):
        """Test creating an issue with missing fields fails with 400."""
        payload = {
            'title': 'Broken desk'
            # Missing facility, description, reporter_name, reporter_email
        }
        response = self.client.post(
            '/api/issues/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_create_issue_invalid_email(self):
        """Test creating an issue with an invalid reporter email fails with 400."""
        payload = {
            'facility': 'Library',
            'title': 'Broken desk',
            'description': 'Desk 4 has a broken leg.',
            'reporter_name': 'Bob',
            'reporter_email': 'not-an-email'
        }
        response = self.client.post(
            '/api/issues/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.get_json()['error'].lower())

    @patch('utils.helpers.User')
    def test_update_issue_status_student_forbidden(self, MockUser):
        """Test students cannot update an issue status (403 Forbidden)."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000001',
            'email': 'student@campus.edu',
            'role': 'student',
            'is_active': True
        }

        payload = {'status': 'resolved'}
        response = self.client.patch(
            '/api/issues/iss1/status',
            data=json.dumps(payload),
            headers=self.student_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    @patch('utils.helpers.User')
    @patch('routes.issues.notify_issue_status_updated')
    @patch('routes.issues.Issue')
    def test_update_issue_status_admin_success(self, MockIssue, MockEmail, MockUser):
        """Test admin can update issue status and trigger email."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        mock_instance = MockIssue.return_value
        mock_instance.update_issue_status.return_value = True
        mock_instance.get_issue_by_id.return_value = {
            '_id': 'iss1',
            'title': 'Leaking pipe',
            'reporter_name': 'Alice',
            'reporter_email': 'alice@campus.edu',
            'status': 'in_progress'
        }

        payload = {'status': 'in_progress'}
        response = self.client.patch(
            '/api/issues/iss1/status',
            data=json.dumps(payload),
            headers=self.admin_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        MockEmail.assert_called_once()
