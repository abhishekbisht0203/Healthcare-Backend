from datetime import date

from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    doctors = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "date_of_birth",
            "gender",
            "blood_group",
            "address",
            "medical_history",
            "allergies",
            "is_active",
            "age",
            "created_by",
            "doctors",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_doctors(self, obj):
        return [
            {"id": doctor.id, "name": doctor.name, "specialization": doctor.specialization}
            for doctor in obj.mappings.select_related("doctor").all()
        ]

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long.")
        return value

    def validate_date_of_birth(self, value):
        today = date.today()
        if value > today:
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        if value.year < 1900:
            raise serializers.ValidationError("Date of birth must be after the year 1900.")
        if (today - value).days // 365 > 120:
            raise serializers.ValidationError("Patient cannot be older than 120 years.")
        return value

    def validate_email(self, value):
        return value.strip().lower()