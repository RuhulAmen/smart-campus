"""Shared rate-limiter instance.

Imported by app.py to initialize against the Flask app, and by
route modules to apply per-endpoint limits.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialized without an app — call limiter.init_app(app) in app.py
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://",
)
