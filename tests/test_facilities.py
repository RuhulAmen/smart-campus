"""Unit and integration tests for Facilities endpoints."""
import json
from unittest.mock import patch
from tests.test_base import BaseTestCase


class TestFacilities(BaseTestCase):
    """Tests for /api/facilities routes."""

    @patch('routes.facilities.Facility')
    def test_get_all_facilities(self, MockFacility):
        """Test retrieving all facilities."""
        MockFacility.return_value.get_all_facilities.return_value = [
            {
                '_id': 'fac1',
                'name': 'Library',
                'location': 'Building A',
                'status': 'operational',
                'description': 'Main study area'
            }
        ]

        response = self.client.get('/api/facilities/')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('facilities', data)
        self.assertEqual(len(data['facilities']), 1)
        self.assertEqual(data['facilities'][0]['name'], 'Library')

    @patch('routes.facilities.Facility')
    def test_get_facility_by_id(self, MockFacility):
        """Test retrieving a single facility by ID."""
        MockFacility.return_value.get_facility_by_id.return_value = {
            '_id': 'fac1',
            'name': 'Library',
            'location': 'Building A',
            'status': 'operational',
            'description': 'Main study area'
        }

        response = self.client.get('/api/facilities/fac1')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['facility']['name'], 'Library')

    @patch('routes.facilities.Facility')
    def test_get_facility_not_found(self, MockFacility):
        """Test retrieving a non-existent facility returns 404."""
        MockFacility.return_value.get_facility_by_id.return_value = None

        response = self.client.get('/api/facilities/nonexistent')
        self.assertEqual(response.status_code, 404)

    @patch('utils.helpers.User')
    def test_create_facility_unauthenticated(self, MockUser):
        """Test unauthenticated request to create facility returns 401."""
        response = self.client.post(
            '/api/facilities/',
            data=json.dumps({'name': 'Gym', 'location': 'Hall C', 'description': 'Fitness center'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

    @patch('utils.helpers.User')
    def test_create_facility_student_forbidden(self, MockUser):
        """Test student cannot create a facility (403 Forbidden)."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000001',
            'email': 'student@campus.edu',
            'role': 'student',
            'is_active': True
        }

        payload = {
            'name': 'Gym',
            'location': 'Building B',
            'description': 'Fitness gym'
        }
        response = self.client.post(
            '/api/facilities/',
            data=json.dumps(payload),
            headers=self.student_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    @patch('utils.helpers.User')
    @patch('routes.facilities.Facility')
    def test_create_facility_admin_success(self, MockFacility, MockUser):
        """Test admin can successfully create a new facility."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        MockFacility.return_value.create_facility.return_value = 'fac_new'
        MockFacility.return_value.get_facility_by_id.return_value = {
            '_id': 'fac_new',
            'name': 'Innovation Lab',
            'location': 'Science Block',
            'description': '3D printers and electronics',
            'status': 'operational'
        }

        payload = {
            'name': 'Innovation Lab',
            'location': 'Science Block',
            'description': '3D printers and electronics',
            'status': 'operational'
        }
        response = self.client.post(
            '/api/facilities/',
            data=json.dumps(payload),
            headers=self.admin_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('facility', data)
        self.assertEqual(data['facility']['_id'], 'fac_new')

    @patch('utils.helpers.User')
    @patch('routes.facilities.Facility')
    def test_update_facility_status_admin(self, MockFacility, MockUser):
        """Test admin updating facility status."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        MockFacility.return_value.update_facility_status.return_value = True

        payload = {'status': 'maintenance'}
        response = self.client.patch(
            '/api/facilities/fac1/status',
            data=json.dumps(payload),
            headers=self.admin_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    @patch('utils.helpers.User')
    def test_update_facility_status_invalid_value(self, MockUser):
        """Test update status fails when value is not in allowed enum."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000002',
            'email': 'admin@campus.edu',
            'role': 'admin',
            'is_active': True
        }
        payload = {'status': 'demolished'}
        response = self.client.patch(
            '/api/facilities/fac1/status',
            data=json.dumps(payload),
            headers=self.admin_auth_headers(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
