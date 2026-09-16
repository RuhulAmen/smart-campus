"""Validation schemas for authentication endpoints."""
from marshmallow import Schema, fields, validate, validates, ValidationError
import re

EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'


class SignupSchema(Schema):
    full_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    email = fields.String(required=True, validate=validate.Length(min=5, max=255))
    student_id = fields.String(required=True, validate=validate.Length(min=1, max=50))
    password = fields.String(required=True, validate=validate.Length(min=6, max=128))

    @validates('email')
    def validate_email(self, value, **kwargs):
        if not re.match(EMAIL_REGEX, value.strip()):
            raise ValidationError('Please enter a valid email address')

    @validates('full_name')
    def validate_full_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError('Full name cannot be empty')


class LoginSchema(Schema):
    email = fields.String(required=True)
    password = fields.String(required=True)


class ProfileUpdateSchema(Schema):
    full_name = fields.String(validate=validate.Length(min=1, max=100))
    email = fields.String(validate=validate.Length(min=5, max=255))
    student_id = fields.String(validate=validate.Length(min=1, max=50))
    password = fields.String(validate=validate.Length(min=6, max=128))

    @validates('email')
    def validate_email(self, value, **kwargs):
        if value and not re.match(EMAIL_REGEX, value.strip()):
            raise ValidationError('Please enter a valid email address')
