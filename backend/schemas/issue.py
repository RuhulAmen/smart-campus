"""Validation schemas for issue endpoints."""
from marshmallow import Schema, fields, validate, validates, ValidationError
import re

EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
VALID_STATUSES = ['pending', 'in_progress', 'resolved', 'rejected']


class IssueCreateSchema(Schema):
    facility = fields.String(required=True, validate=validate.Length(min=1, max=200))
    title = fields.String(required=True, validate=validate.Length(min=1, max=300))
    description = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    reporter_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    reporter_email = fields.String(required=True, validate=validate.Length(min=5, max=255))

    @validates('reporter_email')
    def validate_email(self, value, **kwargs):
        if not re.match(EMAIL_REGEX, value.strip()):
            raise ValidationError('Please enter a valid email address')

    @validates('reporter_name')
    def validate_reporter_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError('Reporter name cannot be empty')


class IssueStatusUpdateSchema(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf(VALID_STATUSES)
    )
