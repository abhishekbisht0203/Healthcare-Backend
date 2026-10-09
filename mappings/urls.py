from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MappingViewSet, PatientMappingsListView

router = DefaultRouter()
router.register("mappings", MappingViewSet, basename="mapping")

urlpatterns = [
    # Declared before the router detail route so the explicit alias wins.
    path("mappings/patient/<int:patient_id>/", PatientMappingsListView.as_view(), name="mapping-patient-list"),
    path("", include(router.urls)),
]