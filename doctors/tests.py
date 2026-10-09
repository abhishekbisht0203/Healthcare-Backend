from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Doctor

User = get_user_model()


class DoctorAPITests(APITestCase):
    list_url = "/api/doctors/"

    def setUp(self):
        self.owner = User.objects.create_user(
            name="Doctor Owner", email="owner@example.com", password="Str0ng-Pass!23"
        )
        self.other = User.objects.create_user(
            name="Other User", email="other@example.com", password="Str0ng-Pass!23"
        )

    def payload(self, **overrides):
        data = {
            "name": "Dr Kavita Iyer",
            "email": "kavita@example.com",
            "phone": "+919812345678",
            "specialization": "cardiology",
            "license_number": "MCI-1001",
            "experience_years": 12,
            "consultation_fee": "750.00",
            "qualification": "MD, DM Cardiology",
            "is_available": True,
        }
        data.update(overrides)
        return data

    def detail_url(self, doctor_id):
        return f"/api/doctors/{doctor_id}/"

    def create_doctor(self, user=None, **overrides):
        return Doctor.objects.create(created_by=user or self.owner, **self.payload(**overrides))

    # --- authentication -----------------------------------------------------

    def test_list_requires_authentication(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        response = self.client.post(self.list_url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- create -------------------------------------------------------------

    def test_create_doctor_assigns_authenticated_user_as_creator(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doctor = Doctor.objects.get(id=response.data["id"])
        self.assertEqual(doctor.created_by, self.owner)

    def test_create_exposes_specialization_display_label(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(), format="json")

        self.assertEqual(response.data["specialization_display"], "Cardiology")

    def test_create_rejects_duplicate_license_number(self):
        self.create_doctor()

        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("license_number", response.data["error"]["details"])

    def test_create_rejects_duplicate_email(self):
        self.create_doctor()

        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_invalid_specialization(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(specialization="astronomy"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_excessive_experience(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(experience_years=95), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_negative_consultation_fee(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(consultation_fee="-10.00"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- list ---------------------------------------------------------------

    def test_list_returns_all_doctors_to_authenticated_user(self):
        """The doctor directory is shared, unlike private patient records."""
        self.create_doctor()
        self.create_doctor(
            name="Dr Other",
            email="other.doctor@example.com",
            license_number="MCI-1002",
        )

        self.client.force_authenticate(self.other)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_list_can_be_filtered_by_specialization(self):
        self.create_doctor()
        self.create_doctor(
            name="Dr Skin",
            email="skin@example.com",
            license_number="MCI-1003",
            specialization="dermatology",
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.list_url, {"specialization": "dermatology"})

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Dr Skin")

    def test_list_supports_search_by_license_number(self):
        self.create_doctor()
        self.create_doctor(
            name="Dr Neuro",
            email="neuro@example.com",
            license_number="NEU-9001",
            specialization="neurology",
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.list_url, {"search": "NEU-9001"})

        self.assertEqual(response.data["count"], 1)

    # --- retrieve -----------------------------------------------------------

    def test_retrieve_doctor_returns_record(self):
        doctor = self.create_doctor()

        self.client.force_authenticate(self.other)
        response = self.client.get(self.detail_url(doctor.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["license_number"], "MCI-1001")

    def test_retrieve_unknown_doctor_returns_404(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.detail_url(999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- update -------------------------------------------------------------

    def test_creator_can_update_doctor(self):
        doctor = self.create_doctor()

        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            self.detail_url(doctor.id), {"is_available": False}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor.refresh_from_db()
        self.assertFalse(doctor.is_available)

    def test_non_creator_cannot_update_doctor(self):
        doctor = self.create_doctor()

        self.client.force_authenticate(self.other)
        response = self.client.patch(
            self.detail_url(doctor.id), {"name": "Dr Hijacked"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        doctor.refresh_from_db()
        self.assertNotEqual(doctor.name, "Dr Hijacked")

    def test_put_update_persists_changes(self):
        doctor = self.create_doctor()

        self.client.force_authenticate(self.owner)
        response = self.client.put(self.detail_url(doctor.id), self.payload(experience_years=15), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor.refresh_from_db()
        self.assertEqual(doctor.experience_years, 15)

    # --- delete -------------------------------------------------------------

    def test_creator_can_delete_doctor(self):
        doctor = self.create_doctor()

        self.client.force_authenticate(self.owner)
        response = self.client.delete(self.detail_url(doctor.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Doctor.objects.filter(id=doctor.id).exists())

    def test_non_creator_cannot_delete_doctor(self):
        doctor = self.create_doctor()

        self.client.force_authenticate(self.other)
        response = self.client.delete(self.detail_url(doctor.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Doctor.objects.filter(id=doctor.id).exists())

    def test_patients_count_reflects_assignments(self):
        doctor = self.create_doctor()
        self.assertEqual(doctor.mappings.count(), 0)

        response_client = self.client
        response_client.force_authenticate(self.owner)
        response = response_client.get(self.detail_url(doctor.id))

        self.assertEqual(response.data["patients_count"], 0)