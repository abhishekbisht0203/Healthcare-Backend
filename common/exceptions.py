"""
Custom exception handler.

Produces a single, predictable error envelope for every API error so that
clients never have to guess at the response shape:

    {
        "success": false,
        "error": {
            "code": "validation_error",
            "message": "Human readable summary.",
            "details": {...}          # optional, field errors
        }
    }
"""

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def _flatten_detail(detail):
    """Turn DRF's nested detail structures into a flat {field: [messages]} map."""
    if not isinstance(detail, dict):
        return None

    flat = {}
    for key, value in detail.items():
        if isinstance(value, (list, tuple)):
            flat[key] = [str(item) for item in value]
        elif isinstance(value, dict):
            flat[key] = [str(item) for item in _flatten_messages(value)]
        else:
            flat[key] = [str(value)]
    return flat


def _flatten_messages(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _flatten_messages(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            yield from _flatten_messages(nested)
    else:
        yield value


def _first_message(detail):
    if isinstance(detail, str):
        return detail
    if isinstance(detail, (list, tuple)):
        return _first_message(detail[0]) if detail else "Request failed."
    if isinstance(detail, dict):
        for value in detail.values():
            return _first_message(value)
    return str(detail)


def _build_response(status_code, code, message, details=None):
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return Response({"success": False, "error": error}, status=status_code)


def custom_exception_handler(exc, context):
    """DRF ``EXCEPTION_HANDLER`` entry point."""

    if isinstance(exc, DjangoValidationError):
        details = _flatten_detail(getattr(exc, "message_dict", None))
        message = _first_message(getattr(exc, "messages", ["Validation failed."]))
        return _build_response(status.HTTP_400_BAD_REQUEST, "validation_error", message, details)

    if isinstance(exc, Http404):
        return _build_response(status.HTTP_404_NOT_FOUND, "not_found", "The requested resource was not found.")

    if isinstance(exc, PermissionDenied):
        return _build_response(status.HTTP_403_FORBIDDEN, "permission_denied", "You do not have permission to perform this action.")

    response = drf_exception_handler(exc, context)

    if response is None:
        if isinstance(exc, IntegrityError):
            return _build_response(
                status.HTTP_409_CONFLICT,
                "conflict",
                "The request conflicts with the current state of the resource.",
            )
        return None

    if isinstance(exc, ValidationError):
        details = _flatten_detail(response.data)
        return _build_response(
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
            _first_message(response.data) or "Validation failed.",
            details,
        )

    if isinstance(exc, APIException):
        code = getattr(exc, "default_code", "api_error")
        message = _first_message(response.data) or "Request failed."
        return _build_response(response.status_code, code, message)

    return response