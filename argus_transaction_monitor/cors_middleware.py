"""
cors_middleware.py — Lightweight CORS middleware for local development.
Allows the customer-app frontend (file:// or localhost) to call the Argus API.
"""
from django.conf import settings
from django.http import HttpResponse


class CorsMiddleware:
    """Add CORS headers to every response during DEBUG mode."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle pre-flight OPTIONS request
        if request.method == "OPTIONS":
            response = HttpResponse()
            self._add_cors_headers(response, request)
            return response

        response = self.get_response(request)
        self._add_cors_headers(response, request)
        return response

    def _add_cors_headers(self, response, request):
        origin = request.META.get("HTTP_ORIGIN", "")
        allow_all = getattr(settings, "CORS_ALLOW_ALL_ORIGINS_IN_DEBUG", False)
        allowed = getattr(settings, "CORS_ALLOWED_ORIGINS", [])

        if settings.DEBUG and (allow_all or origin in allowed or not origin):
            response["Access-Control-Allow-Origin"] = origin or "*"
        elif origin in allowed:
            response["Access-Control-Allow-Origin"] = origin
        else:
            return

        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Requested-With"
        )
        response["Access-Control-Allow-Credentials"] = "true"
