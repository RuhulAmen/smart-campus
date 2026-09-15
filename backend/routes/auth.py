from flask import Blueprint, request, jsonify
from models import User
from utils.helpers import generate_token, token_required
import re
import bcrypt
from utils.limiter import limiter

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'


def _is_valid_email(email):
    return bool(re.match(EMAIL_REGEX, email))


def _public_user(user):
    """Remove sensitive fields and stringify ObjectId for API responses"""
    if not user:
        return None
    user = dict(user)
    user.pop('password', None)
    if '_id' in user:
        user['_id'] = str(user['_id'])
    return user


@auth_bp.route('/signup', methods=['POST'])
@limiter.limit("3 per minute")
def signup():
    """User registration.

    New accounts are always created with the 'student' role. Admins are
    provisioned separately (see backend/create_admin.py) so that users can
    never escalate themselves.
    """
    try:
        data = request.get_json(silent=True) or {}

        # Validate required fields
        required_fields = ['full_name', 'email', 'student_id', 'password']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        full_name = str(data.get('full_name', '')).strip()
        email = str(data.get('email', '')).strip()
        student_id = str(data.get('student_id', '')).strip()
        password = data.get('password', '')

        if not full_name or not email or not student_id or not password:
            return jsonify({'error': 'All fields are required'}), 400

        if not _is_valid_email(email):
            return jsonify({'error': 'Please enter a valid email address'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400

        # Get user model instance
        user_model = User(auth_bp.mongo)

        # Check if user already exists (email check is case-insensitive)
        existing_user = user_model.find_by_email(email)
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400

        # A student ID should belong to a single account
        if user_model.find_by_student_id(student_id):
            return jsonify({'error': 'Student ID already registered'}), 400

        # Create user - always 'student'; role cannot be supplied by the client
        user_id = user_model.create_user(
            full_name=full_name,
            email=email,
            student_id=student_id,
            password=password,
            role='student'
        )

        # Get created user
        user = user_model.find_by_id(user_id)
        user = _public_user(user)

        # Generate token
        token = generate_token(user['_id'], user['email'], user['role'])

        return jsonify({
            'message': 'User created successfully',
            'user': user,
            'token': token
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """User login"""
    try:
        data = request.get_json(silent=True) or {}

        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400

        user_model = User(auth_bp.mongo)
        user = user_model.verify_password(data['email'], data['password'])

        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Generate token
        user = _public_user(user)
        token = generate_token(user['_id'], user['email'], user['role'])

        return jsonify({
            'message': 'Login successful',
            'user': user,
            'token': token
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout.

    Auth is stateless (JWT), so logout is a client-side concern
    (discard the stored token). The endpoint exists for API completeness.
    """
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    """Verify token and get current user"""
    try:
        return jsonify({
            'user': _public_user(current_user),
            'authenticated': True
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get user profile"""
    try:
        user_model = User(auth_bp.mongo)
        user = user_model.find_by_id(current_user['_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': _public_user(user)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Update user profile"""
    try:
        data = request.get_json(silent=True) or {}
        user_model = User(auth_bp.mongo)
        current_id = current_user['_id']

        update_data = {}

        # Full name
        if 'full_name' in data:
            full_name = str(data['full_name']).strip()
            if not full_name:
                return jsonify({'error': 'Full name cannot be empty'}), 400
            update_data['full_name'] = full_name

        # Email (must remain unique and valid)
        if 'email' in data:
            email = str(data['email']).strip()
            if not email:
                return jsonify({'error': 'Email cannot be empty'}), 400
            if not _is_valid_email(email):
                return jsonify({'error': 'Please enter a valid email address'}), 400
            existing = user_model.find_by_email(email)
            if existing and str(existing['_id']) != current_id:
                return jsonify({'error': 'Email already registered'}), 400
            update_data['email'] = email

        # Student ID (must remain unique)
        if 'student_id' in data:
            student_id = str(data['student_id']).strip()
            if not student_id:
                return jsonify({'error': 'Student ID cannot be empty'}), 400
            existing = user_model.find_by_student_id(student_id)
            if existing and str(existing['_id']) != current_id:
                return jsonify({'error': 'Student ID already registered'}), 400
            update_data['student_id'] = student_id

        # Password (optional)
        if 'password' in data and data['password']:
            password = data['password']
            if len(str(password)) < 6:
                return jsonify({'error': 'Password must be at least 6 characters long'}), 400
            hashed = bcrypt.hashpw(str(password).encode('utf-8'), bcrypt.gensalt())
            update_data['password'] = hashed

        if update_data:
            user_model.update_user(current_id, update_data)

        # Get updated user
        user = user_model.find_by_id(current_id)
        return jsonify({
            'message': 'Profile updated successfully',
            'user': _public_user(user)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
