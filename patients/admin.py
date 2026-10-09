from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "gender", "blood_group", "phone", "is_active", "created_by", "created_at")
    list_filter = ("gender", "blood_group", "is_active", "created_at")
    search_fields = ("name", "email", "phone")
    autocomplete_fields = ("created_by",)
    readonly_fields = ("created_at", "updated_at")