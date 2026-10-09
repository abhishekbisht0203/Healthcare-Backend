from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from patients.models import Patient

from .models import PatientDoctorMapping
from .serializers import MappingCreateSerializer, MappingSerializer, PatientDoctorSerializer


class MappingViewSet(viewsets.ModelViewSet):
    """
    Patient <-> doctor assignments.

    Routes
    ------
    ``GET    /api/mappings/``          list assignments
    ``POST   /api/mappings/``          assign a doctor to a patient
    ``GET    /api/mappings/<id>/``     doctors assigned to patient ``<id>``
    ``DELETE /api/mappings/<id>/``     remove the assignment with id ``<id>``
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return MappingCreateSerializer
        return MappingSerializer

    def get_queryset(self):
        queryset = PatientDoctorMapping.objects.select_related("patient", "doctor", "assigned_by")
        user = self.request.user

        if not user.is_staff:
            # Users only see assignments that touch their own patients or doctors.
            queryset = queryset.filter(
                Q(patient__created_by=user) | Q(doctor__created_by=user) | Q(assigned_by=user)
            )

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """``GET /api/mappings/<patient_id>/`` - doctors assigned to a patient."""
        patient = get_object_or_404(Patient.objects.filter(pk=kwargs.get("pk")))

        if not request.user.is_staff and patient.created_by_id != request.user.id:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "permission_denied",
                        "message": "You do not have permission to view this patient's assignments.",
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        mappings = PatientDoctorMapping.objects.filter(patient=patient).select_related("doctor")
        doctors = [dict(PatientDoctorSerializer(m.doctor).data, mapping_id=m.id) for m in mappings]

        return Response(
            {
                "success": True,
                "data": {
                    "patient_id": patient.id,
                    "patient_name": patient.name,
                    "count": len(doctors),
                    "doctors": doctors,
                },
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(assigned_by=request.user)
        return Response(
            {
                "success": True,
                "message": "Doctor assigned to patient successfully.",
                "data": MappingSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        mapping = self.get_object()
        patient_name = mapping.patient.name
        doctor_name = mapping.doctor.name
        mapping.delete()
        return Response(
            {"success": True, "message": f"Dr. {doctor_name} unassigned from {patient_name}."},
            status=status.HTTP_200_OK,
        )


class PatientMappingsListView(ListAPIView):
    """Alias route: ``GET /api/mappings/patient/<patient_id>/``."""

    serializer_class = MappingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PatientDoctorMapping.objects.filter(
            patient_id=self.kwargs["patient_id"]
        ).select_related("patient", "doctor")