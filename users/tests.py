from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterAPITests(APITestCase):
    url = "/api/auth/register/"

    def payload(self, **overrides):
        data = {
            "name": "Dr Asha Mehta",
            "email": "asha@example.com",
            "password": "Str0ng-Pass!23",
            "password_confirm": "Str0ng-Pass!23",
        }
        data.update(overrides)
        return data

    def test_register_returns_user_and_tokens(self):
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"]["tokens"])
        self.assertIn("refresh", response.data["data"]["tokens"])
        self.assertEqual(response.data["data"]["user"]["email"], "asha@example.com")
        self.assertNotIn("password", response.data["data"]["user"])
        self.assertTrue(User.objects.filter(email="asha@example.com").exists())

    def test_password_is_hashed_not_stored_plaintext(self):
        self.client.post(self.url, self.payload(), format="json")

        user = User.objects.get(email="asha@example.com")
        self.assertNotEqual(user.password, "Str0ng-Pass!23")
        self.assertTrue(user.check_password("Str0ng-Pass!23"))

    def test_duplicate_email_is_rejected(self):
        self.client.post(self.url, self.payload(), format="json")
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("email", response.data["error"]["details"])

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(
            self.url, self.payload(password_confirm="Different!123"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data["error"]["details"])

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            self.url, self.payload(password="1234", password_confirm="1234"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(self.url, self.payload(email="not-an-email"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAPITests(APITestCase):
    url = "/api/auth/login/"

    def setUp(self):
        self.user = User.objects.create_user(
            name="Ravi Kumar", email="ravi@example.com", password="Str0ng-Pass!23"
        )

    def test_login_with_valid_credentials_returns_tokens(self):
        response = self.client.post(
            self.url, {"email": "ravi@example.com", "password": "Str0ng-Pass!23"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"]["tokens"])

    def test_login_is_case_insensitive_on_email(self):
        response = self.client.post(
            self.url, {"email": "RAVI@Example.com", "password": "Str0ng-Pass!23"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_with_wrong_password_is_rejected(self):
        response = self.client.post(
            self.url, {"email": "ravi@example.com", "password": "wrong-password"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_login_with_unknown_email_returns_same_message_as_wrong_password(self):
        unknown = self.client.post(
            self.url, {"email": "nobody@example.com", "password": "whatever-123"}, format="json"
        )
        wrong = self.client.post(
            self.url, {"email": "ravi@example.com", "password": "wrong-password"}, format="json"
        )

        # Identical messaging avoids leaking which emails are registered.
        self.assertEqual(
            unknown.data["error"]["message"], wrong.data["error"]["message"]
        )

    def test_inactive_account_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.url, {"email": "ravi@example.com", "password": "Str0ng-Pass!23"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeAPITests(APITestCase):
    url = "/api/auth/me/"

    def setUp(self):
        self.user = User.objects.create_user(
            name="Priya Shah", email="priya@example.com", password="Str0ng-Pass!23"
        )

    def test_me_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], "priya@example.com")


class ChangePasswordAPITests(APITestCase):
    url = "/api/auth/change-password/"

    def setUp(self):
        self.user = User.objects.create_user(
            name="Anil Verma", email="anil@example.com", password="Str0ng-Pass!23"
        )

    def test_change_password_requires_authentication(self):
        response = self.client.patch(
            self.url,
            {"current_password": "Str0ng-Pass!23", "new_password": "N3w-Str0ng!45"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_updates_credentials(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            self.url,
            {"current_password": "Str0ng-Pass!23", "new_password": "N3w-Str0ng!45"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("N3w-Str0ng!45"))

    def test_change_password_rejects_wrong_current_password(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            self.url,
            {"current_password": "not-my-password", "new_password": "N3w-Str0ng!45"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TokenRefreshAPITests(APITestCase):
    url = "/api/auth/refresh/"

    def setUp(self):
        self.user = User.objects.create_user(
            name="Neha Rao", email="neha@example.com", password="Str0ng-Pass!23"
        )

    def test_refresh_exchanges_refresh_token_for_access_token(self):
        login = self.client.post(
            "/api/auth/login/",
            {"email": "neha@example.com", "password": "Str0ng-Pass!23"},
            format="json",
        )
        refresh = login.data["data"]["tokens"]["refresh"]

        response = self.client.post(self.url, {"refresh": refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)