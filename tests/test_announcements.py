"""Unit and integration tests for Announcements endpoints."""
import json
from unittest.mock import patch
from tests.test_base import BaseTestCase


class TestAnnouncements(BaseTestCase):
    """Tests for /api/announcements routes."""

    @patch('routes.announcements.Announcement')
    def test_get_announcements_paginated(self, MockAnnouncement):
        """Test retrieving announcements with pagination."""
        mock_instance = MockAnnouncement.return_value
        mock_instance.get_all_announcements.return_value = [
            {
                '_id': 'ann1',
                'title': 'Campus Power Outage Notice',
                'description': 'Maintenance scheduled for Sunday.',
                'priority': 'high',
                'category': 'Maintenance',
                'status': 'active'
            }
        ]
        mock_instance.count_filtered_announcements.return_value = 1

        response = self.client.get('/api/announcements/?page=1&limit=5&priority=high')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('announcements', data)
        self.assertEqual(data['total'], 1)
        self.assertEqual(len(data['announcements']), 1)
        self.assertEqual(data['announcements'][0]['title'], 'Campus Power Outage Notice')

    @patch('utils.helpers.User')
    def test_create_announcement_student_forbidden(self, MockUser):
        """Test students cannot create announcements (403 Forbidden)."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000001',
            'email': 'student@campus.edu',
            'role': 'student',
            'is_active': True
        }

        payload = {
            'title': 'Student Party',
            'description': 'Party at the hall',
            'priority': 'low',
            'category': 'Social'
        }
        response = self.client.post(
            '/api/announcements/',
            data=json.dumps(payload),
            headers=self.student_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    @patch('utils.helpers.User')
    @patch('routes.announcements.Announcement')
    def test_create_announcement_admin_success(self, MockAnnouncement, MockUser):
        """Test admin can successfully create an announcement."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        MockAnnouncement.return_value.create_announcement.return_value = 'ann_new'
        MockAnnouncement.return_value.get_announcement_by_id.return_value = {
            '_id': 'ann_new',
            'title': 'Library Extended Hours',
            'description': 'The library will remain open until midnight during finals week.',
            'priority': 'medium',
            'category': 'Academics'
        }

        payload = {
            'title': 'Library Extended Hours',
            'description': 'The library will remain open until midnight during finals week.',
            'priority': 'medium',
            'category': 'Academics'
        }
        response = self.client.post(
            '/api/announcements/',
            data=json.dumps(payload),
            headers=self.admin_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('announcement', data)
        self.assertEqual(data['announcement']['_id'], 'ann_new')

    @patch('utils.helpers.User')
    def test_create_announcement_invalid_priority(self, MockUser):
        """Test creating announcement with invalid priority fails with 400."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }

        payload = {
            'title': 'Notice',
            'description': 'Some description',
            'priority': 'urgent_now',  # Not in ['high', 'medium', 'low']
            'category': 'General'
        }
        response = self.client.post(
            '/api/announcements/',
            data=json.dumps(payload),
            headers=self.admin_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
