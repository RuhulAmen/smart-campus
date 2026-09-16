"""Unit and integration tests for Health check, PWA assets, and Uploads."""
import io
from unittest.mock import patch, MagicMock
from tests.test_base import BaseTestCase


class TestHealthAndStatic(BaseTestCase):
    """Tests for health monitoring, static PWA assets, and file uploads."""

    def test_health_check_endpoint(self):
        """Test that /api/health responds with JSON structure."""
        response = self.client.get('/api/health/')
        self.assertIn(response.status_code, [200, 503])
        data = response.get_json()
        self.assertIn('service', data)
        self.assertEqual(data['service'], 'smart-campus-api')
        self.assertIn('checks', data)
        self.assertIn('database', data['checks'])

    def test_pWA_manifest_serving(self):
        """Test that manifest.json is served with 200 OK and valid JSON."""
        response = self.client.get('/manifest.json')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['short_name'], 'SmartCampus')
        self.assertEqual(data['display'], 'standalone')
        self.assertIn('icons', data)

    def test_service_worker_serving(self):
        """Test that sw.js is served with 200 OK and cache logic."""
        response = self.client.get('/sw.js')
        self.assertEqual(response.status_code, 200)
        js_text = response.get_data(as_text=True)
        self.assertIn('smart-campus-v1', js_text)
        self.assertIn('CACHE_NAME', js_text)

    def test_root_index_serving(self):
        """Test that / returns the frontend index.html."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html_text = response.get_data(as_text=True)
        self.assertIn('Smart Campus', html_text)

    def test_upload_missing_file(self):
        """Test upload endpoint rejects requests without file part."""
        response = self.client.post('/api/uploads/')
        self.assertEqual(response.status_code, 400)
        self.assertIn('No file part', response.get_json()['error'])

    def test_upload_disallowed_extension(self):
        """Test upload endpoint rejects dangerous file types (e.g. .exe)."""
        data = {
            'file': (io.BytesIO(b'malicious script content'), 'virus.exe')
        }
        response = self.client.post(
            '/api/uploads/',
            data=data,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('not allowed', response.get_json()['error'].lower())

    def test_upload_valid_image(self):
        """Test upload endpoint accepts valid images (.png)."""
        data = {
            'file': (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'), 'photo.png')
        }
        response = self.client.post(
            '/api/uploads/',
            data=data,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 201)
        res_data = response.get_json()
        self.assertIn('url', res_data)
        self.assertTrue(res_data['url'].startswith('/uploads/'))
