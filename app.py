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

# Secret key configuration
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    if os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        logger.warning("⚠️ SECRET_KEY is not set in Vercel Environment Variables! Using temporary fallback.")
        secret_key = 'smart-campus-temporary-secret-key-please-set-in-vercel'
    else:
        raise RuntimeError(
            "SECRET_KEY is not set. Copy backend/.env.example to backend/.env and set a unique "
            "SECRET_KEY, e.g. python -c \"import secrets; print(secrets.token_hex(32))\""
        )
app.config['SECRET_KEY'] = secret_key

# Fail fast instead of hanging for ~30s on every request when the DB is unreachable
MONGO_TIMEOUT_MS = int(os.getenv('MONGO_SERVER_SELECTION_TIMEOUT_MS', '5000'))

# Initialize MongoDB. Validate URI format and provide graceful fallback so serverless functions boot
try:
    app.mongo = PyMongo(app, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
except Exception as e:
    logger.error("Failed to initialize PyMongo with MONGO_URI: %s", e)
    fallback_uri = os.getenv('MONGO_FALLBACK_URI', 'mongodb://localhost:27017/smart_campus')
    logger.warning("Falling back to %s so application can still start", fallback_uri)
    app.config['MONGO_URI'] = fallback_uri
    try:
        app.mongo = PyMongo(app, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
    except Exception as fallback_err:
        logger.error("Fallback PyMongo initialization also failed: %s", fallback_err)
        app.mongo = None

# Absolute paths to static asset directories (prefer public, fallback to frontend)
PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'public'))
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'frontend'))
STATIC_DIRS = [d for d in (PUBLIC_DIR, FRONTEND_DIR) if os.path.isdir(d)]

# Absolute path to the uploads directory (use /tmp in serverless environments like Vercel)
if os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception as e:
    logger.warning("Could not create uploads directory: %s", e)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Import models and routes (resolved from backend directory added to sys.path above)
from models import Facility  # type: ignore
from routes import register_routes  # type: ignore
from utils.db_indexes import ensure_indexes  # type: ignore

# Register routes
register_routes(app)

# Create database indexes (idempotent — safe to call on every startup)
if app.mongo:
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
    """Seed default facilities once the database is reachable."""
    global _data_initialized, _last_init_attempt

    # Don't hold up static file requests (HTML, CSS, JS) or if mongo is not initialized
    if not app.mongo or _data_initialized or not request.path.startswith('/api'):
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
@app.route('/api/index')
@app.route('/api/index.py')
def serve_frontend():
    for d in STATIC_DIRS:
        idx = os.path.join(d, 'index.html')
        if os.path.isfile(idx):
            return send_from_directory(d, 'index.html', mimetype='text/html')
    return jsonify({'error': 'Application frontend not found'}), 404


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/<path:path>')
def serve_static(path):
    # Normalize path if Vercel or proxy forwarded using rewritten destination prefix
    clean_path = path
    for prefix in ('api/index/', 'api/index.py/', 'api/'):
        if clean_path.startswith(prefix):
            clean_path = clean_path[len(prefix):]
            break

    # Strip query parameters if appended to path
    clean_path = clean_path.split('?')[0]

    # Explicit MIME-type determination for rock-solid stylesheet/script delivery
    mime_type = None
    lower_path = clean_path.lower()
    if lower_path.endswith('.css'):
        mime_type = 'text/css'
    elif lower_path.endswith('.js'):
        mime_type = 'application/javascript'
    elif lower_path.endswith('.json'):
        mime_type = 'application/json'
    elif lower_path.endswith('.html'):
        mime_type = 'text/html'
    elif lower_path.endswith('.png'):
        mime_type = 'image/png'
    elif lower_path.endswith(('.jpg', '.jpeg')):
        mime_type = 'image/jpeg'
    elif lower_path.endswith('.svg'):
        mime_type = 'image/svg+xml'
    elif lower_path.endswith('.ico'):
        mime_type = 'image/x-icon'

    for directory in STATIC_DIRS:
        # Check direct path
        file_path = os.path.join(directory, clean_path)
        if os.path.isfile(file_path):
            return send_from_directory(directory, clean_path, mimetype=mime_type)

        # Check lowercase / uppercase CSS variation
        if clean_path.startswith('css/'):
            alt_path = 'CSS/' + clean_path[4:]
            if os.path.isfile(os.path.join(directory, alt_path)):
                return send_from_directory(directory, alt_path, mimetype='text/css')
        elif clean_path.startswith('CSS/'):
            alt_path = 'css/' + clean_path[4:]
            if os.path.isfile(os.path.join(directory, alt_path)):
                return send_from_directory(directory, alt_path, mimetype='text/css')

        # Check clean URL (.html extension omitted)
        html_file = file_path + '.html'
        if os.path.isfile(html_file):
            return send_from_directory(directory, clean_path + '.html', mimetype='text/html')

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
