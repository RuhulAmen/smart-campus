"""Health check endpoint for uptime monitoring.

Pinged by hosting platforms (Render, Railway, etc.) and monitoring
tools to verify the application and database are responsive.
"""
from flask import Blueprint, jsonify, current_app
import time

health_bp = Blueprint('health', __name__)


@health_bp.route('/', methods=['GET'], strict_slashes=False)
def health_check():
    """Returns application health status including database connectivity."""
    result = {
        'status': 'healthy',
        'service': 'smart-campus-api',
        'checks': {}
    }
    status_code = 200

    # Database check
    try:
        start = time.monotonic()
        current_app.mongo.db.command('ping')
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        result['checks']['database'] = {
            'status': 'connected',
            'latency_ms': latency_ms,
        }
    except Exception as e:
        result['status'] = 'unhealthy'
        result['checks']['database'] = {
            'status': 'disconnected',
            'error': str(e),
        }
        status_code = 503

    return jsonify(result), status_code

