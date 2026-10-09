import json

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class ErrorEnvelopeTests(APITestCase):
    """The API must always answer with the same error shape."""

    def setUp(self):
        self.user = User.objects.create_user(
            name="Envelope User", email="envelope@example.com", password="Str0ng-Pass!23"
        )

    def test_not_found_uses_standard_envelope(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/patients/999999/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
        self.assertIn("code", response.data["error"])
        self.assertIn("message", response.data["error"])

    def test_unauthenticated_uses_standard_envelope(self):
        response = self.client.get("/api/patients/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])
        self.assertIn("error", response.data)

    def test_validation_error_includes_field_details(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/patients/", {"name": "X"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("details", response.data["error"])
        self.assertIn("phone", response.data["error"]["details"])

    def test_unknown_route_returns_404(self):
        response = self.client.get("/api/does-not-exist/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ApiRootTests(APITestCase):
    def test_root_lists_endpoints(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The root is a plain Django JsonResponse, not a DRF Response.
        payload = json.loads(response.content)
        self.assertEqual(payload["service"], "Healthcare Backend API")
        self.assertIn("auth", payload["endpoints"])
        self.assertIn("patients", payload["endpoints"])
        self.assertIn("doctors", payload["endpoints"])
        self.assertIn("mappings", payload["endpoints"])