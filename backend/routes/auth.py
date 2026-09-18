from flask import Blueprint, request, jsonify
from models import User
from utils.helpers import generate_token, token_required
import re
import bcrypt
from utils.limiter import limiter
from utils.validation import validate_request
from schemas import SignupSchema, LoginSchema, ProfileUpdateSchema

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
        data, error = validate_request(SignupSchema)
        if error:
            return error

        full_name = data['full_name'].strip()
        email = data['email'].strip()
        student_id = data['student_id'].strip()
        password = data['password']

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
        if "Connection refused" in str(e) or "Timeout" in type(e).__name__ or "ServerSelectionTimeoutError" in type(e).__name__:
            return jsonify({'error': 'Database connection failed. Please check network access and MongoDB cluster status.'}), 503
        err_type = type(e).__name__
        err_msg = str(e)
        if "Connection refused" in err_msg or "Timeout" in err_type or "ServerSelectionTimeoutError" in err_type or "AutoReconnect" in err_type:
            detail = err_msg.split('\n')[0] if err_msg else err_type
            if len(detail) > 120:
                detail = detail[:120] + '...'
            return jsonify({'error': f'Database connection error: {detail}. Verify Atlas IP access (0.0.0.0/0) and credentials.'}), 503
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """User login"""
    try:
        data, error = validate_request(LoginSchema)
        if error:
            return error

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
        if "Connection refused" in str(e) or "Timeout" in type(e).__name__ or "ServerSelectionTimeoutError" in type(e).__name__:
            return jsonify({'error': 'Database connection failed. Please check network access and MongoDB cluster status.'}), 503
        err_type = type(e).__name__
        err_msg = str(e)
        if "Connection refused" in err_msg or "Timeout" in err_type or "ServerSelectionTimeoutError" in err_type or "AutoReconnect" in err_type:
            detail = err_msg.split('\n')[0] if err_msg else err_type
            if len(detail) > 120:
                detail = detail[:120] + '...'
            return jsonify({'error': f'Database connection error: {detail}. Verify Atlas IP access (0.0.0.0/0) and credentials.'}), 503
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
        data, error = validate_request(ProfileUpdateSchema)
        if error:
            return error
        user_model = User(auth_bp.mongo)
        current_id = current_user['_id']

        update_data = {}

        # Schema already validated types and lengths; now check uniqueness
        if 'full_name' in data:
            update_data['full_name'] = data['full_name'].strip()

        if 'email' in data:
            email = data['email'].strip()
            existing = user_model.find_by_email(email)
            if existing and str(existing['_id']) != current_id:
                return jsonify({'error': 'Email already registered'}), 400
            update_data['email'] = email

        if 'student_id' in data:
            student_id = data['student_id'].strip()
            existing = user_model.find_by_student_id(student_id)
            if existing and str(existing['_id']) != current_id:
                return jsonify({'error': 'Student ID already registered'}), 400
            update_data['student_id'] = student_id

        if 'password' in data:
            hashed = bcrypt.hashpw(str(data['password']).encode('utf-8'), bcrypt.gensalt())
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
