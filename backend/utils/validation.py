"""Request validation utilities using Marshmallow schemas."""
from flask import request, jsonify
from marshmallow import ValidationError


def validate_request(schema_class):
    """Validate request JSON against a Marshmallow schema.

    Returns (validated_data, None) on success or (None, error_response) on failure.
    Usage:
        data, error = validate_request(SignupSchema)
        if error:
            return error
    """
    raw = request.get_json(silent=True) or {}
    schema = schema_class()
    try:
        data = schema.load(raw)
        return data, None
    except ValidationError as err:
        # Return first error message for each field
        messages = err.messages
        # Flatten to a single human-readable string
        errors = []
        for field, msgs in messages.items():
            if isinstance(msgs, list):
                errors.append(f"{field}: {msgs[0]}")
            else:
                errors.append(f"{field}: {msgs}")
        return None, (jsonify({'error': '; '.join(errors)}), 400)
