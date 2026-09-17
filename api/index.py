import os
import sys

# Add project root and backend directory to sys.path so app, models, and routes resolve
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

backend_dir = os.path.join(root_dir, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Expose the Flask instance as 'app' for Vercel's serverless Python runtime
from app import app  # type: ignore


class VercelPathNormalizer:
    """WSGI middleware ensuring correct PATH_INFO when Vercel rewrites requests."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        # If Vercel rewrote the path to the function entrypoint destination:
        if path_info in ('/api/index', '/api/index.py', 'api/index', 'api/index.py'):
            real_path = (
                environ.get('HTTP_X_FORWARDED_URI') or
                environ.get('HTTP_X_MATCHED_PATH') or
                environ.get('RAW_URI') or
                environ.get('REQUEST_URI')
            )
            if real_path:
                clean_path = real_path.split('?')[0]
                if clean_path and clean_path not in ('/api/index', '/api/index.py'):
                    environ['PATH_INFO'] = clean_path

        return self.wsgi_app(environ, start_response)


# Wrap Flask's wsgi_app to protect against Vercel internal rewrite path overrides
app.wsgi_app = VercelPathNormalizer(app.wsgi_app)

