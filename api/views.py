from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView

from core.authz import HasKCRealmRole
from hospital.models import (
    UserProfile, Pole, Region, District, Commune, Facility, Department,
    Practitioner, Bed, Patient, PatientResidence, Kinship, Encounter,
    BedOccupancy, Procedure, DiagnosticReport, Observation, Payer,
    Invoice, InvoiceLine, Appointment, Referral, CodeAct, CodeDiagICD10, CodeLabLOINC
)
from .serializers import *
from .permissions import IsStaff, IsPatient, ReadOnly, StaffOrReadOnly, IsSelfPatient
from .filters import EncounterFilter, AppointmentFilter, ObservationFilter, InvoiceFilter


class AdminOnlyView(APIView):
    permission_classes = [HasKCRealmRole]
    required_roles = {"admin"}

    def get(self, request):
        return Response({"ok": True})


# ------------- Base Mixins -------------
class DefaultsMixin:
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    ordering_fields = "__all__"
    search_fields = ()
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]


# ------------- Reference data -------------
class PoleViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Pole.objects.all().order_by("name")
    serializer_class = PoleSerializer
    permission_classes = [StaffOrReadOnly]
    search_fields = ("name",)


class RegionViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Region.objects.select_related("pole").all().order_by("name")
    serializer_class = RegionSerializer
    permission_classes = [StaffOrReadOnly]
    search_fields = ("name", "pole__name")


class DistrictViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = District.objects.select_related("region").all().order_by("name")
    serializer_class = DistrictSerializer
    permission_classes = [StaffOrReadOnly]
    search_fields = ("name", "region__name")


class CommuneViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Commune.objects.select_related("district").all().order_by("name")
    serializer_class = CommuneSerializer
    permission_classes = [StaffOrReadOnly]
    search_fields = ("name", "district__name")


# ------------- Patient -------------
class PatientViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by("-created_at")
    serializer_class = PatientSerializer
    permission_classes = [IsStaff]
    search_fields = ("mpi", "family_name", "given_name")

    @action(detail=True, methods=["get"], url_path="siblings")
    def siblings(self, request, pk=None):
        patient = self.get_object()
        qs = patient.siblings_via_parents
        data = PatientSerializer(qs, many=True).data
        return Response(data)


class PatientResidenceViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = PatientResidence.objects.select_related("patient", "commune").all().order_by("-from_date")
    serializer_class = PatientResidenceSerializer
    permission_classes = [IsStaff]
    search_fields = ("patient__mpi", "commune__name")


class KinshipViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Kinship.objects.select_related("src", "dst").all()
    serializer_class = KinshipSerializer
    permission_classes = [IsStaff]
    search_fields = ("src__mpi", "dst__mpi", "relation")


# ------------- Appointments / Referrals -------------
class AppointmentViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related("patient", "practitioner", "facility", "department").all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsStaff]
    filterset_class = AppointmentFilter
    search_fields = ("status", "patient__mpi", "practitioner__matricule")
    ordering = ("-start_at",)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        obj = self.get_object()
        if obj.status in ("CANCELLED", "DONE"):
            return Response({"detail": "Already closed."}, status=400)
        obj.status = "CANCELLED"
        obj.save()
        return Response(self.get_serializer(obj).data)


# ------------- Code Systems (read-only) -------------
class ReadOnlyModelViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [ReadOnly]


class CodeActViewSet(ReadOnlyModelViewSet):
    queryset = CodeAct.objects.all().order_by("code")
    serializer_class = CodeActSerializer
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("code", "label")
    ordering_fields = "__all__"


class CodeICD10ViewSet(ReadOnlyModelViewSet):
    queryset = CodeDiagICD10.objects.all().order_by("icd10")
    serializer_class = CodeICD10Serializer
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("icd10", "label")
    ordering_fields = "__all__"


class CodeLOINCViewSet(ReadOnlyModelViewSet):
    queryset = CodeLabLOINC.objects.all().order_by("loinc")
    serializer_class = CodeLOINCSerializer
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("loinc", "label")
    ordering_fields = "__all__"


# ------------- User Profiles -------------
class UserProfileViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = UserProfile.objects.select_related("facility").all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsStaff]
    search_fields = ("username", "idp_sub", "tenant_key")


# ------------- /me/* endpoints (patient portail) -------------
class MyEncountersViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = EncounterSerializer
    permission_classes = [IsSelfPatient]
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering = ("-start_at",)

    def get_queryset(self):
        # RLS limite déjà sur patient_mpi
        return Encounter.objects.select_related("facility", "department", "patient").order_by("-start_at")


class MyObservationsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ObservationSerializer
    permission_classes = [IsSelfPatient]
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering = ("-observed_at",)

    def get_queryset(self):
        return Observation.objects.select_related("encounter", "report").order_by("-observed_at")


class MyInvoicesViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsSelfPatient]
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering = ("-issued_at", "-created_at")

    def get_queryset(self):
        return Invoice.objects.select_related("encounter", "payer").order_by("-issued_at", "-created_at")
