from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import EncounterFilter, ObservationFilter
from api.permissions import IsStaff, StaffOrReadOnly
from api.serializers import EncounterSerializer, BedOccupancySerializer, ProcedureSerializer, ReferralSerializer, \
    ObservationSerializer, DiagnosticReportSerializer, VisitTypeSerializer, PractitionerSerializer, BedSerializer, \
    FacilitySerializer, DepartmentSerializer
from api.views import DefaultsMixin
from hospital.models import Encounter, BedOccupancy, Procedure, Referral, Observation, DiagnosticReport, VisitType, \
    Practitioner, Bed, Facility, Department


class FacilityViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Facility.objects.select_related("parent", "region", "district", "commune").all().order_by("name")
    serializer_class = FacilitySerializer
    permission_classes = [StaffOrReadOnly]
    search_fields = ("name", "code", "type")


class DepartmentViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Department.objects.select_related("facility").all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [IsStaff]
    search_fields = ("name", "code", "facility__code")

class PractitionerViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Practitioner.objects.select_related("facility", "department").all().order_by("matricule")
    serializer_class = PractitionerSerializer
    permission_classes = [IsStaff]
    search_fields = ("matricule", "specialty", "facility__code")


class BedViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Bed.objects.select_related("facility", "department").all().order_by("code")
    serializer_class = BedSerializer
    permission_classes = [IsStaff]
    search_fields = ("code", "department__name", "facility__code")


# ------------- Clinical -------------
class VisitTypeViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = VisitType.objects.all().order_by("sort_order", "code")
    serializer_class = VisitTypeSerializer
    permission_classes = [StaffOrReadOnly]
    search_fields = ("code", "label", "category")
    ordering = ("sort_order", "code")


class EncounterViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Encounter.objects.select_related("patient", "facility", "department").all()
    serializer_class = EncounterSerializer
    permission_classes = [IsStaff]
    filterset_class = EncounterFilter
    search_fields = ("patient__mpi", "facility__code", "visit_type")
    ordering = ("-start_at",)

    @action(detail=True, methods=["post"], url_path="discharge")
    def discharge(self, request, pk=None):
        obj = self.get_object()
        if obj.end_at:
            return Response({"detail": "Already closed."}, status=400)
        obj.end_at = request.data.get("end_at") or obj.end_at or obj.start_at
        obj.outcome = request.data.get("outcome", "DISCHARGED")
        obj.save()
        return Response(self.get_serializer(obj).data)


class BedOccupancyViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = BedOccupancy.objects.select_related("bed", "patient").all()
    serializer_class = BedOccupancySerializer
    permission_classes = [IsStaff]
    ordering = ("-from_ts",)


class ProcedureViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Procedure.objects.select_related("encounter", "performer").all()
    serializer_class = ProcedureSerializer
    permission_classes = [IsStaff]
    search_fields = ("code", "name", "encounter__patient__mpi")
    ordering = ("-performed_at",)


class DiagnosticReportViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = DiagnosticReport.objects.select_related("encounter").all()
    serializer_class = DiagnosticReportSerializer
    permission_classes = [IsStaff]
    search_fields = ("modality", "status", "encounter__patient__mpi")
    ordering = ("-issued_at",)


class ObservationViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Observation.objects.select_related("encounter", "report").all()
    serializer_class = ObservationSerializer
    permission_classes = [IsStaff]
    filterset_class = ObservationFilter
    search_fields = ("loinc_code", "encounter__patient__mpi")
    ordering = ("-observed_at",)


class ReferralViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Referral.objects.select_related("from_facility", "to_facility", "patient").all()
    serializer_class = ReferralSerializer
    permission_classes = [IsStaff]
    search_fields = ("status", "patient__mpi", "from_facility__code", "to_facility__code")
    ordering = ("-created_at",)
