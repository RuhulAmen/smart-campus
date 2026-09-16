"""Validation schemas for admin user management endpoints."""
from marshmallow import Schema, fields, validate


class UserRoleUpdateSchema(Schema):
    role = fields.String(
        required=True,
        validate=validate.OneOf(['student', 'admin'])
    )


class UserStatusUpdateSchema(Schema):
    is_active = fields.Boolean(required=True)

