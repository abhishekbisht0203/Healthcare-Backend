from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from doctors.models import Doctor
from patients.models import Patient

from .models import PatientDoctorMapping

User = get_user_model()


class MappingAPITests(APITestCase):
    list_url = "/api/mappings/"

    def setUp(self):
        self.owner = User.objects.create_user(
            name="Mapping Owner", email="owner@example.com", password="Str0ng-Pass!23"
        )
        self.other = User.objects.create_user(
            name="Other User", email="other@example.com", password="Str0ng-Pass!23"
        )
        self.patient = Patient.objects.create(
            created_by=self.owner,
            name="Mapped Patient",
            phone="+919800000001",
            date_of_birth="1988-03-15",
        )
        self.doctor = Doctor.objects.create(
            created_by=self.owner,
            name="Dr Assigned",
            email="assigned@example.com",
            phone="+919800000002",
            specialization="cardiology",
            license_number="MCI-2001",
        )

    def detail_url(self, mapping_id):
        return f"/api/mappings/{mapping_id}/"

    # --- authentication -----------------------------------------------------

    def test_list_requires_authentication(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        response = self.client.post(
            self.list_url, {"patient_id": self.patient.id, "doctor_id": self.doctor.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- create -------------------------------------------------------------

    def test_create_mapping_using_id_fields(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.list_url,
            {"patient_id": self.patient.id, "doctor_id": self.doctor.id, "notes": "Follow-up in 2 weeks"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        mapping = PatientDoctorMapping.objects.get(id=response.data["data"]["id"])
        self.assertEqual(mapping.assigned_by, self.owner)
        self.assertEqual(mapping.patient, self.patient)
        self.assertEqual(mapping.doctor, self.doctor)

    def test_create_mapping_using_nested_pk_fields(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.list_url, {"patient": self.patient.id, "doctor": self.doctor.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_rejects_duplicate_assignment(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.list_url, {"patient_id": self.patient.id, "doctor_id": self.doctor.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_assign_doctor_to_another_users_patient(self):
        foreign_patient = Patient.objects.create(
            created_by=self.other,
            name="Foreign Patient",
            phone="+919800000003",
            date_of_birth="1975-11-02",
        )

        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.list_url, {"patient_id": foreign_patient.id, "doctor_id": self.doctor.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PatientDoctorMapping.objects.filter(patient=foreign_patient).exists())

    def test_create_rejects_unknown_patient(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.list_url, {"patient_id": 999999, "doctor_id": self.doctor.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- list ---------------------------------------------------------------

    def test_list_shows_assignments_touching_users_records(self):
        mine = PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], mine.id)

    def test_list_hides_unrelated_assignments(self):
        """Assignments where the user owns neither the patient nor the doctor."""
        foreign_patient = Patient.objects.create(
            created_by=self.other,
            name="Foreign Patient",
            phone="+919800000004",
            date_of_birth="1990-01-01",
        )
        foreign_doctor = Doctor.objects.create(
            created_by=self.other,
            name="Dr Foreign",
            email="foreign@example.com",
            phone="+919800000007",
            specialization="neurology",
            license_number="MCI-2002",
        )
        PatientDoctorMapping.objects.create(patient=foreign_patient, doctor=foreign_doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.list_url)

        self.assertEqual(response.data["count"], 0)

    def test_list_includes_readable_names(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.list_url)

        row = response.data["results"][0]
        self.assertEqual(row["patient_name"], self.patient.name)
        self.assertEqual(row["doctor_name"], self.doctor.name)
        self.assertEqual(row["doctor_specialization"], "Cardiology")

    # --- retrieve (doctors for a patient) -----------------------------------

    def test_retrieve_by_patient_id_lists_assigned_doctors(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.detail_url(self.patient.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["doctors"][0]["name"], self.doctor.name)
        self.assertIn("mapping_id", response.data["data"]["doctors"][0])

    def test_retrieve_by_patient_id_returns_empty_list_when_none_assigned(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.detail_url(self.patient.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 0)

    def test_retrieve_another_users_patient_is_forbidden(self):
        foreign_patient = Patient.objects.create(
            created_by=self.other,
            name="Foreign Patient",
            phone="+919800000005",
            date_of_birth="1960-06-06",
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.detail_url(foreign_patient.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_alias_route_lists_patient_mappings(self):
        mapping = PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/mappings/patient/{self.patient.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], mapping.id)

    # --- delete -------------------------------------------------------------

    def test_delete_removes_assignment(self):
        mapping = PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.delete(self.detail_url(mapping.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PatientDoctorMapping.objects.filter(id=mapping.id).exists())

    def test_delete_unrelated_mapping_is_forbidden(self):
        """A user who owns neither record involved cannot remove the assignment."""
        other_patient = Patient.objects.create(
            created_by=self.other,
            name="Other Patient",
            phone="+919800000006",
            date_of_birth="1999-09-09",
        )
        other_doctor = Doctor.objects.create(
            created_by=self.other,
            name="Dr Other",
            email="other.doctor@example.com",
            phone="+919800000008",
            specialization="dermatology",
            license_number="MCI-2003",
        )
        mapping = PatientDoctorMapping.objects.create(patient=other_patient, doctor=other_doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.delete(self.detail_url(mapping.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(PatientDoctorMapping.objects.filter(id=mapping.id).exists())

    def test_doctor_owner_can_remove_assignment_for_someone_elses_patient(self):
        """Participating in the assignment is enough to remove it."""
        other_patient = Patient.objects.create(
            created_by=self.other,
            name="Other Patient",
            phone="+919800000009",
            date_of_birth="1999-09-09",
        )
        mapping = PatientDoctorMapping.objects.create(patient=other_patient, doctor=self.doctor)

        self.client.force_authenticate(self.owner)
        response = self.client.delete(self.detail_url(mapping.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PatientDoctorMapping.objects.filter(id=mapping.id).exists())

    def test_deleting_patient_cascades_to_mappings(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)

        self.patient.delete()

        self.assertEqual(PatientDoctorMapping.objects.count(), 0)