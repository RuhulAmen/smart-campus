"""Base test case with helper fixtures for Smart Campus tests."""
import unittest
import datetime
import jwt
from unittest.mock import patch, MagicMock

import app as app_module
from utils.limiter import limiter


class BaseTestCase(unittest.TestCase):
    """Base class for all Smart Campus API tests."""

    @classmethod
    def setUpClass(cls):
        cls.app = app_module.app
        cls.app.config['TESTING'] = True
        cls.app.config['RATELIMIT_ENABLED'] = False
        limiter.enabled = False
        cls.client = cls.app.test_client()
        cls.secret = cls.app.config['SECRET_KEY']

    def create_token(self, user_id="600000000000000000000001", email="student@test.com", role="student"):
        """Generate a valid signed JWT for test requests."""
        payload = {
            'user_id': str(user_id),
            'email': email,
            'role': role,
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)
        }
        return jwt.encode(payload, self.secret, algorithm='HS256')

    def auth_headers(self, token):
        """Return Authorization header dict."""
        return {'Authorization': f'Bearer {token}'}

    def student_auth_headers(self):
        token = self.create_token(
            user_id="600000000000000000000001",
            email="student@campus.edu",
            role="student"
        )
        return self.auth_headers(token)

    def admin_auth_headers(self):
        token = self.create_token(
            user_id="600000000000000000000002",
            email="admin@campus.edu",
            role="admin"
        )
        return self.auth_headers(token)

