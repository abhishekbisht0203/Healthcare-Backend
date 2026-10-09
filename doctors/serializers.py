from rest_framework import serializers

from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    specialization_display = serializers.CharField(source="get_specialization_display", read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    patients_count = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "specialization",
            "specialization_display",
            "license_number",
            "experience_years",
            "consultation_fee",
            "qualification",
            "is_available",
            "patients_count",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_patients_count(self, obj):
        return obj.mappings.count()

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long.")
        return value

    def validate_experience_years(self, value):
        if value > 70:
            raise serializers.ValidationError("Experience cannot exceed 70 years.")
        return value

    def validate_email(self, value):
        return value.strip().lower()