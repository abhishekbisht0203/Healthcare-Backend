from django.conf import settings
from django.db import models


class PatientDoctorMapping(models.Model):
    """Associates a patient with a doctor (a doctor assignment)."""

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="mappings",
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="mappings",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_mappings",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_doctor_mappings"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "doctor"],
                name="unique_patient_doctor_assignment",
            )
        ]
        indexes = [
            models.Index(fields=["patient", "-created_at"]),
            models.Index(fields=["doctor"]),
        ]

    def __str__(self):
        return f"{self.patient.name} -> Dr. {self.doctor.name}"