from flask import Blueprint

# Import blueprints
from .auth import auth_bp
from .facilities import facilities_bp
from .announcements import announcements_bp
from .issues import issues_bp
from .dashboard import dashboard_bp
from .health import health_bp
from .uploads import uploads_bp
from .admin import admin_bp

def register_routes(app):
    # PASS THE MONGO DB TO THE BLUEPRINTS HERE (This fixes the circular import!)
    auth_bp.mongo = app.mongo
    facilities_bp.mongo = app.mongo
    announcements_bp.mongo = app.mongo
    issues_bp.mongo = app.mongo
    dashboard_bp.mongo = app.mongo
    health_bp.mongo = app.mongo
    admin_bp.mongo = app.mongo

    # Register the blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(facilities_bp, url_prefix='/api/facilities')
    app.register_blueprint(announcements_bp, url_prefix='/api/announcements')
    app.register_blueprint(issues_bp, url_prefix='/api/issues')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(health_bp, url_prefix='/api/health')
    app.register_blueprint(uploads_bp, url_prefix='/api/uploads')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')