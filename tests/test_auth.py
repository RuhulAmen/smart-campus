"""Unit and integration tests for Authentication endpoints."""
import json
from unittest.mock import patch, MagicMock
from tests.test_base import BaseTestCase


class TestAuth(BaseTestCase):
    """Tests for /api/auth routes."""

    @patch('routes.auth.User')
    def test_signup_success(self, MockUser):
        """Test successful registration with valid inputs."""
        mock_instance = MockUser.return_value
        mock_instance.find_by_email.return_value = None
        mock_instance.find_by_student_id.return_value = None
        mock_instance.create_user.return_value = '600000000000000000000001'
        mock_instance.find_by_id.return_value = {
            '_id': '600000000000000000000001',
            'full_name': 'John Doe',
            'email': 'johndoe@campus.edu',
            'student_id': 'ST12345',
            'role': 'student',
            'password': b'hashed'
        }

        payload = {
            'full_name': 'John Doe',
            'email': 'johndoe@campus.edu',
            'student_id': 'ST12345',
            'password': 'password123'
        }

        response = self.client.post(
            '/api/auth/signup',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['email'], 'johndoe@campus.edu')
        self.assertEqual(data['user']['role'], 'student')
        self.assertNotIn('password', data['user'])

    def test_signup_missing_fields(self):
        """Test that signup fails when required fields are missing."""
        payload = {
            'email': 'johndoe@campus.edu',
            'password': 'password123'
        }
        response = self.client.post(
            '/api/auth/signup',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)

    def test_signup_invalid_email(self):
        """Test that signup fails with an invalid email address."""
        payload = {
            'full_name': 'John Doe',
            'email': 'not-an-email',
            'student_id': 'ST12345',
            'password': 'password123'
        }
        response = self.client.post(
            '/api/auth/signup',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('valid email', data['error'].lower())

    def test_signup_short_password(self):
        """Test that signup fails with password under 6 chars."""
        payload = {
            'full_name': 'John Doe',
            'email': 'john@campus.edu',
            'student_id': 'ST12345',
            'password': '123'
        }
        response = self.client.post(
            '/api/auth/signup',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    @patch('routes.auth.User')
    def test_signup_duplicate_email(self, MockUser):
        """Test that signup fails when email is already registered."""
        mock_instance = MockUser.return_value
        mock_instance.find_by_email.return_value = {'_id': 'existing'}

        payload = {
            'full_name': 'John Doe',
            'email': 'existing@campus.edu',
            'student_id': 'ST99999',
            'password': 'password123'
        }
        response = self.client.post(
            '/api/auth/signup',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Email already registered', response.get_json()['error'])

    @patch('routes.auth.User')
    def test_signup_duplicate_student_id(self, MockUser):
        """Test that signup fails when student ID is already registered."""
        mock_instance = MockUser.return_value
        mock_instance.find_by_email.return_value = None
        mock_instance.find_by_student_id.return_value = {'_id': 'existing'}

        payload = {
            'full_name': 'John Doe',
            'email': 'new@campus.edu',
            'student_id': 'ST_EXISTING',
            'password': 'password123'
        }
        response = self.client.post(
            '/api/auth/signup',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Student ID already registered', response.get_json()['error'])

    @patch('routes.auth.User')
    def test_login_success(self, MockUser):
        """Test successful login returns token and user payload."""
        mock_instance = MockUser.return_value
        mock_instance.verify_password.return_value = {
            '_id': '600000000000000000000001',
            'email': 'student@campus.edu',
            'role': 'student',
            'full_name': 'Test Student',
            'password': b'hashed'
        }

        payload = {'email': 'student@campus.edu', 'password': 'password123'}
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('token', data)
        self.assertEqual(data['user']['email'], 'student@campus.edu')
        self.assertNotIn('password', data['user'])

    @patch('routes.auth.User')
    def test_login_invalid_credentials(self, MockUser):
        """Test login fails with incorrect password."""
        mock_instance = MockUser.return_value
        mock_instance.verify_password.return_value = None

        payload = {'email': 'student@campus.edu', 'password': 'wrongpassword'}
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn('Invalid credentials', response.get_json()['error'])

    @patch('utils.helpers.User')
    def test_verify_token_success(self, MockUser):
        """Test /api/auth/verify with valid token."""
        MockUser.return_value.find_by_id.return_value = {
            '_id': '600000000000000000000001',
            'email': 'student@campus.edu',
            'role': 'student',
            'is_active': True
        }

        response = self.client.get(
            '/api/auth/verify',
            headers=self.student_auth_headers()
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['authenticated'])
        self.assertEqual(data['user']['email'], 'student@campus.edu')

    def test_verify_token_unauthenticated(self):
        """Test /api/auth/verify rejects missing token."""
        response = self.client.get('/api/auth/verify')
        self.assertEqual(response.status_code, 401)

    @patch('utils.helpers.User')
    @patch('routes.auth.User')
    def test_get_profile(self, MockAuthUser, MockHelperUser):
        """Test /api/auth/profile returns user details."""
        user_record = {
            '_id': '600000000000000000000001',
            'email': 'student@campus.edu',
            'role': 'student',
            'full_name': 'Test Student',
            'is_active': True
        }
        MockHelperUser.return_value.find_by_id.return_value = user_record
        MockAuthUser.return_value.find_by_id.return_value = user_record

        response = self.client.get(
            '/api/auth/profile',
            headers=self.student_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['user']['full_name'], 'Test Student')

