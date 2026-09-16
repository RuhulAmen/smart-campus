from flask import Blueprint, request, jsonify
from models import Facility
from utils.helpers import token_required, admin_required
from utils.validation import validate_request
from schemas import FacilityCreateSchema, FacilityUpdateSchema, FacilityStatusSchema

facilities_bp = Blueprint('facilities', __name__)

# strict_slashes=False: the SPA calls these without a trailing slash, so without
# it every request gets an extra 308 redirect (and breaks cross-origin POSTs).
@facilities_bp.route('/', methods=['GET'], strict_slashes=False)
def get_facilities():
    """Get all facilities"""
    try:
        facility_model = Facility(facilities_bp.mongo)
        facilities = facility_model.get_all_facilities()
        
        # Convert ObjectId to string
        for facility in facilities:
            facility['_id'] = str(facility['_id'])
        
        return jsonify({'facilities': facilities}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@facilities_bp.route('/<facility_id>', methods=['GET'])
def get_facility(facility_id):
    """Get a specific facility"""
    try:
        facility_model = Facility(facilities_bp.mongo)
        facility = facility_model.get_facility_by_id(facility_id)
        
        if not facility:
            return jsonify({'error': 'Facility not found'}), 404
        
        facility['_id'] = str(facility['_id'])
        return jsonify({'facility': facility}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@facilities_bp.route('/', methods=['POST'], strict_slashes=False)
@token_required
@admin_required
def create_facility(current_user):
    """Create a new facility (Admin only)"""
    try:
        data, error = validate_request(FacilityCreateSchema)
        if error:
            return error
        
        facility_model = Facility(facilities_bp.mongo)
        facility_id = facility_model.create_facility(
            name=data['name'],
            location=data['location'],
            description=data['description'],
            status=data.get('status', 'operational')
        )
        
        facility = facility_model.get_facility_by_id(facility_id)
        facility['_id'] = str(facility['_id'])
        
        return jsonify({
            'message': 'Facility created successfully',
            'facility': facility
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@facilities_bp.route('/<facility_id>', methods=['PUT'])
@token_required
@admin_required
def update_facility(current_user, facility_id):
    """Update facility (Admin only)"""
    try:
        data, error = validate_request(FacilityUpdateSchema)
        if error:
            return error
        facility_model = Facility(facilities_bp.mongo)
        
        # Check if facility exists
        facility = facility_model.get_facility_by_id(facility_id)
        if not facility:
            return jsonify({'error': 'Facility not found'}), 404
        
        # Schema already strips unknown fields; use validated data directly
        update_data = {k: v for k, v in data.items() if v is not None}
        
        if update_data:
            facility_model.update_facility(facility_id, update_data)
        
        # Get updated facility
        updated_facility = facility_model.get_facility_by_id(facility_id)
        updated_facility['_id'] = str(updated_facility['_id'])
        
        return jsonify({
            'message': 'Facility updated successfully',
            'facility': updated_facility
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@facilities_bp.route('/<facility_id>/status', methods=['PATCH'])
@token_required
@admin_required
def update_facility_status(current_user, facility_id):
    """Update facility status (Admin only)"""
    try:
        data, error = validate_request(FacilityStatusSchema)
        if error:
            return error
        
        facility_model = Facility(facilities_bp.mongo)
        
        # Check if facility exists
        facility = facility_model.get_facility_by_id(facility_id)
        if not facility:
            return jsonify({'error': 'Facility not found'}), 404
        
        # Update status
        facility_model.update_status(facility_id, data['status'])
        
        return jsonify({
            'message': 'Facility status updated successfully',
            'status': data['status']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@facilities_bp.route('/<facility_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_facility(current_user, facility_id):
    """Delete facility (Admin only)"""
    try:
        facility_model = Facility(facilities_bp.mongo)
        
        # Check if facility exists
        facility = facility_model.get_facility_by_id(facility_id)
        if not facility:
            return jsonify({'error': 'Facility not found'}), 404
        
        facility_model.delete_facility(facility_id)
        
        return jsonify({'message': 'Facility deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@facilities_bp.route('/initialize', methods=['POST'])
@token_required
@admin_required
def initialize_facilities(current_user):
    """Initialize default facilities (Admin only)"""
    try:
        facility_model = Facility(facilities_bp.mongo)
        result = facility_model.initialize_default_facilities()
        
        if result:
            return jsonify({'message': 'Default facilities initialized'}), 201
        else:
            return jsonify({'message': 'Facilities already exist'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500