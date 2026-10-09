from django.contrib import admin

from .models import PatientDoctorMapping


@admin.register(PatientDoctorMapping)
class PatientDoctorMappingAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "is_active", "assigned_by", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("patient__name", "doctor__name")
    autocomplete_fields = ("patient", "doctor")
    readonly_fields = ("created_at", "updated_at")