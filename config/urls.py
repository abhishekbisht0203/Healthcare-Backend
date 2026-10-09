"""Root URL configuration for the Healthcare Backend API."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root(request):
    """Lightweight discovery document listing the available endpoints."""
    return JsonResponse(
        {
            "service": "Healthcare Backend API",
            "version": "1.0.0",
            "endpoints": {
                "auth": {
                    "register": "/api/auth/register/",
                    "login": "/api/auth/login/",
                    "refresh": "/api/auth/refresh/",
                    "me": "/api/auth/me/",
                    "change_password": "/api/auth/change-password/",
                },
                "patients": {
                    "list_create": "/api/patients/",
                    "detail": "/api/patients/<id>/",
                },
                "doctors": {
                    "list_create": "/api/doctors/",
                    "detail": "/api/doctors/<id>/",
                },
                "mappings": {
                    "list_create": "/api/mappings/",
                    "patient_detail": "/api/mappings/<patient_id>/",
                    "alias": "/api/mappings/patient/<patient_id>/",
                    "delete": "/api/mappings/<id>/",
                },
                "admin": "/admin/",
            },
        }
    )


urlpatterns = [
    path("", api_root, name="api-root"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/", include("patients.urls")),
    path("api/", include("doctors.urls")),
    path("api/", include("mappings.urls")),
]