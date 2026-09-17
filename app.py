from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
import sys
import time
from flask_limiter import Limiter  # type: ignore
from flask_limiter.util import get_remote_address  # type: ignore
import logging

logger = logging.getLogger(__name__)

# Ensure backend directory is in sys.path so models, routes, and utils can be imported directly
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load .env: support both root .env and backend/.env regardless of working directory
root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))
backend_env = os.path.abspath(os.path.join(backend_dir, '.env'))
if os.path.exists(root_env):
    load_dotenv(root_env)
if os.path.exists(backend_env):
    load_dotenv(backend_env)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for the configured frontend origins (comma-separated in .env)
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000')
cors_origins = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
CORS(app, origins=cors_origins)

# Rate limiting — import the shared instance so route modules can decorate endpoints
from utils.limiter import limiter  # type: ignore
limiter.init_app(app)

# Load configuration from environment variables
mongo_uri = os.getenv('MONGO_URI')
if not mongo_uri:
    if os.getenv('VERCEL'):
        logger.error(
            "⚠️ MONGO_URI is NOT set in Vercel Environment Variables! "
            "Please configure MONGO_URI in your Vercel project settings: Settings -> Environment Variables."
        )
    mongo_uri = 'mongodb://localhost:27017/smart_campus'
app.config['MONGO_URI'] = mongo_uri
app.config['MONGO_DB_NAME'] = os.getenv('MONGO_DB_NAME', 'smart_campus')
app.config['JWT_EXPIRATION_HOURS'] = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

# No hardcoded secret: a default key in source control lets anyone forge tokens
# (including admin ones), so refuse to start without a real one.
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError(
        "SECRET_KEY is not set. Copy backend/.env.example to backend/.env and set a unique "
        "SECRET_KEY, e.g. python -c \"import secrets; print(secrets.token_hex(32))\""
    )

# Fail fast instead of hanging for ~30s on every request when the DB is unreachable
MONGO_TIMEOUT_MS = int(os.getenv('MONGO_SERVER_SELECTION_TIMEOUT_MS', '5000'))

# Initialize MongoDB. Validate URI format and provide explicit guidance on failure.
try:
    app.mongo = PyMongo(app, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
except Exception as e:
    logger.error("Failed to initialize PyMongo with MONGO_URI: %s", e)
    fallback_uri = os.getenv('MONGO_FALLBACK_URI')
    if fallback_uri:
        logger.warning("Falling back to explicitly configured MONGO_FALLBACK_URI: %s", fallback_uri)
        app.config['MONGO_URI'] = fallback_uri
        app.mongo = PyMongo(app, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
    else:
        raise RuntimeError(
            f"Failed to initialize MongoDB with MONGO_URI: {e}. "
            f"If your database password contains special characters (like '@', ':', or '/'), "
            f"they must be percent-encoded (e.g. '@' -> '%40')."
        ) from e

# Absolute path to the frontend directory
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'frontend'))

# Absolute path to the uploads directory for issue photo attachments
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Import models and routes (resolved from backend directory added to sys.path above)
from models import Facility  # type: ignore
from routes import register_routes  # type: ignore
from utils.db_indexes import ensure_indexes  # type: ignore

# Register routes
register_routes(app)

# Create database indexes (idempotent — safe to call on every startup)
try:
    ensure_indexes(app.mongo)
except Exception:
    pass  # Logged inside ensure_indexes; don't block startup

# Seed default data a single time (guarded so it works under any server/entrypoint)
_data_initialized = False
_last_init_attempt = 0.0
# If the DB is offline, don't retry on every request (each attempt costs a timeout)
_INIT_RETRY_SECONDS = int(os.getenv('SEED_RETRY_SECONDS', '60'))


@app.before_request
def initialize_data():
    """Seed default facilities once the database is reachable.

    The guard is only set after a successful seed: marking it beforehand meant
    that a database which was offline during the first API request left the
    defaults unseeded for the entire life of the process. A cooldown keeps an
    offline database from being retried on every single request.
    """
    global _data_initialized, _last_init_attempt

    # Don't hold up static file requests (HTML, CSS, JS)
    if _data_initialized or not request.path.startswith('/api'):
        return

    now = time.monotonic()
    if now - _last_init_attempt < _INIT_RETRY_SECONDS:
        return
    _last_init_attempt = now

    try:
        facility_model = Facility(app.mongo)
        facility_model.initialize_default_facilities()
        _data_initialized = True
        logger.info("Default facilities initialized")
    except Exception as e:
        logger.warning("Could not initialize default facilities (will retry): %s", e)


# Serve frontend files
@app.route('/')
def serve_frontend():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/<path:path>')
def serve_static(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return jsonify({'error': 'Resource not found'}), 404


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=port)
