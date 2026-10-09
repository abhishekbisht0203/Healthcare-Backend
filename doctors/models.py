from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class Doctor(models.Model):
    class Specialization(models.TextChoices):
        GENERAL_MEDICINE = "general_medicine", "General Medicine"
        CARDIOLOGY = "cardiology", "Cardiology"
        DERMATOLOGY = "dermatology", "Dermatology"
        NEUROLOGY = "neurology", "Neurology"
        PEDIATRICS = "pediatrics", "Pediatrics"
        ORTHOPEDICS = "orthopedics", "Orthopedics"
        GASTROENTEROLOGY = "gastroenterology", "Gastroenterology"
        PSYCHIATRY = "psychiatry", "Psychiatry"
        RADIOLOGY = "radiology", "Radiology"
        SURGERY = "surgery", "Surgery"
        ONCOLOGY = "oncology", "Oncology"

    phone_validator = RegexValidator(
        regex=r"^\+?[1-9]\d{7,14}$",
        message="Enter a valid phone number (8-15 digits, optional + prefix).",
    )

    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    specialization = models.CharField(max_length=50, choices=Specialization.choices)
    license_number = models.CharField(max_length=50, unique=True)
    experience_years = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    consultation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    qualification = models.CharField(max_length=200, blank=True)
    is_available = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctors",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "doctors"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["specialization"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"Dr. {self.name} - {self.get_specialization_display()}"