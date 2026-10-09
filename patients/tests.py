from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Patient

User = get_user_model()


class PatientAPITests(APITestCase):
    list_url = "/api/patients/"

    def setUp(self):
        self.owner = User.objects.create_user(
            name="Owner One", email="owner1@example.com", password="Str0ng-Pass!23"
        )
        self.other = User.objects.create_user(
            name="Other User", email="other@example.com", password="Str0ng-Pass!23"
        )

    def payload(self, **overrides):
        data = {
            "name": "Ravi Patient",
            "email": "ravi.patient@example.com",
            "phone": "+919876543210",
            "date_of_birth": "1990-05-20",
            "gender": "male",
            "blood_group": "O+",
            "address": "12 MG Road",
            "medical_history": "None",
            "allergies": "Penicillin",
        }
        data.update(overrides)
        return data

    def detail_url(self, patient_id):
        return f"/api/patients/{patient_id}/"

    def create_patient(self, user=None, **overrides):
        user = user or self.owner
        return Patient.objects.create(created_by=user, **self.payload(**overrides))

    # --- authentication -----------------------------------------------------

    def test_list_requires_authentication(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        response = self.client.post(self.list_url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- create -------------------------------------------------------------

    def test_create_patient_assigns_authenticated_user_as_creator(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        patient = Patient.objects.get(id=response.data["id"])
        self.assertEqual(patient.created_by, self.owner)

    def test_created_patient_reports_computed_age(self):
        dob = date.today() - timedelta(days=365 * 30)
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(date_of_birth=dob.isoformat()), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(response.data["age"], (29, 30))

    def test_patient_serializer_lists_assigned_doctors(self):
        """The nested ``doctors`` field must unwrap mapping rows to doctors."""
        from doctors.models import Doctor
        from mappings.models import PatientDoctorMapping

        patient = self.create_patient()
        doctor = Doctor.objects.create(
            created_by=self.owner,
            name="Dr Nested",
            email="nested@example.com",
            phone="+919800000123",
            specialization="cardiology",
            license_number="MCI-9999",
        )
        PatientDoctorMapping.objects.create(patient=patient, doctor=doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.detail_url(patient.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["doctors"]), 1)
        self.assertEqual(response.data["doctors"][0]["name"], "Dr Nested")
        self.assertEqual(response.data["doctors"][0]["id"], doctor.id)

    def test_create_rejects_future_date_of_birth(self):
        self.client.force_authenticate(self.owner)
        future = (date.today() + timedelta(days=1)).isoformat()
        response = self.client.post(self.list_url, self.payload(date_of_birth=future), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_invalid_phone(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(phone="12"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_short_name(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(name="A"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_invalid_gender(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url, self.payload(gender="unknown-value"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- list / scoping -----------------------------------------------------

    def test_list_returns_only_patients_created_by_request_user(self):
        mine = self.create_patient()
        self.create_patient(user=self.other, name="Someone Else")

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in response.data["results"]]
        self.assertIn(mine.id, ids)
        self.assertEqual(len(ids), 1)

    def test_list_can_be_filtered_by_gender(self):
        self.create_patient(gender="male")
        self.create_patient(name="Second Patient", gender="female")

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.list_url, {"gender": "female"})

        names = [row["name"] for row in response.data["results"]]
        self.assertEqual(names, ["Second Patient"])

    def test_list_supports_search_by_name(self):
        self.create_patient(name="Findable Person")
        self.create_patient(name="Hidden Person")

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.list_url, {"search": "Findable"})

        names = [row["name"] for row in response.data["results"]]
        self.assertEqual(names, ["Findable Person"])

    # --- retrieve -----------------------------------------------------------

    def test_retrieve_own_patient_returns_record(self):
        patient = self.create_patient()

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.detail_url(patient.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], patient.name)

    def test_retrieve_another_users_patient_returns_404(self):
        patient = self.create_patient(user=self.other)

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.detail_url(patient.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- update -------------------------------------------------------------

    def test_owner_can_update_patient(self):
        patient = self.create_patient()

        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            self.detail_url(patient.id), {"name": "Ravi Updated"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient.refresh_from_db()
        self.assertEqual(patient.name, "Ravi Updated")

    def test_put_update_persists_changes(self):
        patient = self.create_patient()
        data = self.payload(name="Full Replace Name")

        self.client.force_authenticate(self.owner)
        response = self.client.put(self.detail_url(patient.id), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient.refresh_from_db()
        self.assertEqual(patient.name, "Full Replace Name")

    def test_non_owner_cannot_update_patient(self):
        patient = self.create_patient(user=self.other)

        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            self.detail_url(patient.id), {"name": "Hijacked"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        patient.refresh_from_db()
        self.assertNotEqual(patient.name, "Hijacked")

    # --- delete -------------------------------------------------------------

    def test_owner_can_delete_patient(self):
        patient = self.create_patient()

        self.client.force_authenticate(self.owner)
        response = self.client.delete(self.detail_url(patient.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=patient.id).exists())

    def test_non_owner_cannot_delete_patient(self):
        patient = self.create_patient(user=self.other)

        self.client.force_authenticate(self.owner)
        response = self.client.delete(self.detail_url(patient.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Patient.objects.filter(id=patient.id).exists())

    def test_staff_can_update_another_users_patient(self):
        patient = self.create_patient(user=self.other)
        self.owner.is_staff = True
        self.owner.save(update_fields=["is_staff"])

        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            self.detail_url(patient.id), {"name": "Staff Edited"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient.refresh_from_db()
        self.assertEqual(patient.name, "Staff Edited")