from django.contrib import admin

from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "specialization", "license_number", "experience_years", "is_available", "created_by")
    list_filter = ("specialization", "is_available")
    search_fields = ("name", "email", "license_number")
    autocomplete_fields = ("created_by",)
    readonly_fields = ("created_at", "updated_at")