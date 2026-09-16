"""Image file upload route for maintenance issue reports."""
import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from utils.limiter import limiter

uploads_bp = Blueprint('uploads', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@uploads_bp.route('/', methods=['POST'], strict_slashes=False)
@limiter.limit("30 per hour")
def upload_file():
    """Upload an image file (max 5MB, png/jpg/jpeg/gif/webp)."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({
            'error': f"File type not allowed. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        }), 400

    # Ensure uploads directory exists
    upload_folder = current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'))
    )
    os.makedirs(upload_folder, exist_ok=True)

    # Generate unique filename to prevent collisions and overwrite attacks
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(upload_folder, unique_name)

    # Read and check size
    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({'error': 'File size exceeds 5MB limit'}), 400

    with open(file_path, 'wb') as f:
        f.write(file_bytes)

    # Return relative URL for static serving
    file_url = f"/uploads/{unique_name}"
    return jsonify({
        'message': 'File uploaded successfully',
        'url': file_url,
        'filename': unique_name
    }), 201

