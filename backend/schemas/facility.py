"""Validation schemas for facility endpoints."""
from marshmallow import Schema, fields, validate


VALID_STATUSES = ['operational', 'maintenance', 'closed']


class FacilityCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    location = fields.String(required=True, validate=validate.Length(min=1, max=200))
    description = fields.String(required=True, validate=validate.Length(min=1, max=1000))
    status = fields.String(
        load_default='operational',
        validate=validate.OneOf(VALID_STATUSES)
    )


class FacilityUpdateSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=200))
    location = fields.String(validate=validate.Length(min=1, max=200))
    description = fields.String(validate=validate.Length(min=1, max=1000))
    status = fields.String(validate=validate.OneOf(VALID_STATUSES))


class FacilityStatusSchema(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf(VALID_STATUSES)
    )
