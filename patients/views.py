from rest_framework import viewsets

from common.permissions import IsOwnerOrReadOnly

from .models import Patient
from .serializers import PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """
    CRUD for patient records.

    * Any authenticated user can read patient records.
    * Only the creator (or staff) can create, update or delete a record.
    * ``GET /api/patients/`` is scoped to the records of the request user.
    """

    serializer_class = PatientSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filterset_fields = ["gender", "blood_group", "is_active"]
    search_fields = ["name", "email", "phone"]
    ordering_fields = ["created_at", "name"]

    def get_queryset(self):
        queryset = Patient.objects.select_related("created_by").prefetch_related("mappings__doctor")
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(created_by=user)

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)