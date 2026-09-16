"""Validation schemas for announcement endpoints."""
from marshmallow import Schema, fields, validate


VALID_PRIORITIES = ['high', 'medium', 'low']


class AnnouncementCreateSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=300))
    description = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    priority = fields.String(required=True, validate=validate.OneOf(VALID_PRIORITIES))
    category = fields.String(required=True, validate=validate.Length(min=1, max=100))


class AnnouncementUpdateSchema(Schema):
    title = fields.String(validate=validate.Length(min=1, max=300))
    description = fields.String(validate=validate.Length(min=1, max=5000))
    priority = fields.String(validate=validate.OneOf(VALID_PRIORITIES))
    category = fields.String(validate=validate.Length(min=1, max=100))
