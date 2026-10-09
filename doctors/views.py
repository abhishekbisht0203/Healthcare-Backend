from rest_framework import viewsets

from common.permissions import IsOwnerOrReadOnly

from .models import Doctor
from .serializers import DoctorSerializer


class DoctorViewSet(viewsets.ModelViewSet):
    """
    CRUD for doctor records.

    * Any authenticated user can browse the doctor directory.
    * Only the creator (or staff) can update or delete a doctor record.
    """

    serializer_class = DoctorSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filterset_fields = ["specialization", "is_available"]
    search_fields = ["name", "email", "phone", "license_number"]
    ordering_fields = ["created_at", "name", "experience_years", "consultation_fee"]

    def get_queryset(self):
        queryset = Doctor.objects.select_related("created_by").prefetch_related("mappings")
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)