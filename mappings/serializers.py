from rest_framework import serializers

from doctors.models import Doctor
from patients.models import Patient

from .models import PatientDoctorMapping


class MappingSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(source="patient.id", read_only=True)
    doctor_id = serializers.IntegerField(source="doctor.id", read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    doctor_specialization = serializers.CharField(
        source="doctor.get_specialization_display", read_only=True
    )
    assigned_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = (
            "id",
            "patient",
            "patient_id",
            "patient_name",
            "doctor",
            "doctor_id",
            "doctor_name",
            "doctor_specialization",
            "notes",
            "is_active",
            "assigned_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "assigned_by", "created_at", "updated_at")

    def validate_patient(self, value):
        request = self.context.get("request")
        if request and not request.user.is_staff and value.created_by_id != request.user.id:
            raise serializers.ValidationError(
                "You can only assign doctors to your own patients."
            )
        return value

    def validate_doctor(self, value):
        # Doctors live in a shared directory, so any authenticated user may
        # assign them; the record keeps its original creator.
        return value

    def validate(self, attrs):
        patient = attrs.get("patient")
        doctor = attrs.get("doctor")

        if patient is not None and doctor is not None:
            duplicate = PatientDoctorMapping.objects.filter(patient=patient, doctor=doctor)
            if self.instance:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"doctor": "This doctor is already assigned to this patient."}
                )

        return attrs


class MappingCreateSerializer(MappingSerializer):
    """Accepts ``patient_id`` / ``doctor_id`` from the request body."""

    class Meta(MappingSerializer.Meta):
        pass

    def to_internal_value(self, data):
        data = dict(data)

        if "patient" not in data and data.get("patient_id"):
            data["patient"] = data.get("patient_id")
        if "doctor" not in data and data.get("doctor_id"):
            data["doctor"] = data.get("doctor_id")

        return super().to_internal_value(data)


class PatientDoctorSerializer(serializers.ModelSerializer):
    """Compact doctor representation returned by ``GET /api/mappings/<patient_id>/``."""

    mapping_id = serializers.IntegerField(source="id", read_only=True)
    specialization = serializers.CharField(read_only=True)
    specialization_display = serializers.CharField(source="get_specialization_display", read_only=True)

    class Meta:
        model = Doctor
        fields = (
            "mapping_id",
            "id",
            "name",
            "specialization",
            "specialization_display",
            "phone",
            "email",
            "experience_years",
            "is_available",
        )