"""Unit and integration tests for Admin management and CSV export endpoints."""
import json
from unittest.mock import patch
from tests.test_base import BaseTestCase


class TestAdmin(BaseTestCase):
    """Tests for /api/admin routes."""

    @patch('utils.helpers.User')
    def test_admin_routes_reject_student(self, MockUser):
        """Test student role is forbidden from accessing admin endpoints."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000001',
            'email': 'student@campus.edu',
            'role': 'student',
            'is_active': True
        }

        # Test users list
        res = self.client.get('/api/admin/users', headers=self.student_auth_headers())
        self.assertEqual(res.status_code, 403)

        # Test issues CSV export
        res = self.client.get('/api/admin/export/issues.csv', headers=self.student_auth_headers())
        self.assertEqual(res.status_code, 403)

        # Test facilities CSV export
        res = self.client.get('/api/admin/export/facilities.csv', headers=self.student_auth_headers())
        self.assertEqual(res.status_code, 403)

    @patch('utils.helpers.User')
    @patch('routes.admin.User')
    def test_list_users_admin_success(self, MockAdminUser, MockHelperUser):
        """Test admin listing users with pagination."""
        admin_record = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        MockHelperUser.return_value.find_by_id.return_value = admin_record
        mock_instance = MockAdminUser.return_value
        mock_instance.collection.count_documents.return_value = 2
        mock_cursor = [
            admin_record,
            {
                '_id': '600000000000000000000001',
                'email': 'student@campus.edu',
                'role': 'student',
                'is_active': True
            }
        ]
        # mock chain: find().sort().skip().limit()
        mock_find = mock_instance.collection.find.return_value
        mock_find.sort.return_value.skip.return_value.limit.return_value = mock_cursor

        response = self.client.get('/api/admin/users?page=1&limit=10', headers=self.admin_auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('users', data)
        self.assertEqual(data['total'], 2)

    @patch('utils.helpers.User')
    @patch('routes.admin.User')
    def test_change_user_role_success(self, MockAdminUser, MockHelperUser):
        """Test admin promoting a student to admin."""
        admin_record = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        MockHelperUser.return_value.find_by_id.return_value = admin_record

        mock_instance = MockAdminUser.return_value
        mock_instance.find_by_id.return_value = {
            '_id': '600000000000000000000001',
            'email': 'student@campus.edu',
            'role': 'student'
        }
        mock_instance.update_user.return_value = True

        payload = {'role': 'admin'}
        response = self.client.patch(
            '/api/admin/users/600000000000000000000001/role',
            data=json.dumps(payload),
            headers=self.admin_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['role'], 'admin')

    @patch('utils.helpers.User')
    def test_admin_self_demotion_prevented(self, MockHelperUser):
        """Test admin cannot demote themselves."""
        admin_record = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        MockHelperUser.return_value.find_by_id.return_value = admin_record

        payload = {'role': 'student'}
        # Admin trying to demote their own user id
        response = self.client.patch(
            '/api/admin/users/600000000000000000000002/role',
            data=json.dumps(payload),
            headers=self.admin_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot revoke your own administrator privileges', response.get_json()['error'].lower())

    @patch('utils.helpers.User')
    def test_admin_self_deactivation_prevented(self, MockHelperUser):
        """Test admin cannot deactivate their own account."""
        admin_record = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        MockHelperUser.return_value.find_by_id.return_value = admin_record

        payload = {'is_active': False}
        response = self.client.patch(
            '/api/admin/users/600000000000000000000002/status',
            data=json.dumps(payload),
            headers=self.admin_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot deactivate your own account', response.get_json()['error'])

    @patch('utils.helpers.User')
    @patch('routes.admin.Issue')
    def test_export_issues_csv_success(self, MockIssue, MockHelperUser):
        """Test admin can export issues CSV with correct columns."""
        MockHelperUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        MockIssue.return_value.get_all_issues.return_value = [
            {
                '_id': 'iss_csv_1',
                'facility': 'Computer Lab 3',
                'title': 'Monitor not working',
                'description': 'Power button does not respond',
                'status': 'pending',
                'reporter_name': 'Charlie',
                'reporter_email': 'charlie@campus.edu',
                'image_url': '/uploads/mon.png',
                'date': '2026-09-16'
            }
        ]

        response = self.client.get(
            '/api/admin/export/issues.csv',
            headers=self.admin_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv; charset=utf-8')
        csv_content = response.get_data(as_text=True)
        self.assertIn('Issue ID,Facility,Title', csv_content)
        self.assertIn('Computer Lab 3', csv_content)
        self.assertIn('Monitor not working', csv_content)
        self.assertIn('Yes', csv_content)  # Photo attached flag

    @patch('utils.helpers.User')
    @patch('routes.admin.Facility')
    def test_export_facilities_csv_success(self, MockFacility, MockHelperUser):
        """Test admin can export facilities CSV with correct columns."""
        MockHelperUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        MockFacility.return_value.get_all_facilities.return_value = [
            {
                '_id': 'fac_csv_1',
                'name': 'Gymnasium',
                'location': 'Sports Complex',
                'status': 'operational',
                'description': 'Main sports hall'
            }
        ]

        response = self.client.get(
            '/api/admin/export/facilities.csv',
            headers=self.admin_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv; charset=utf-8')
        csv_content = response.get_data(as_text=True)
        self.assertIn('Facility ID,Name,Location', csv_content)
        self.assertIn('Gymnasium', csv_content)
        self.assertIn('Sports Complex', csv_content)
