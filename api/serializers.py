from rest_framework import serializers
from hospital.models import (
    UserProfile, Pole, Region, District, Commune, Facility, Department,
    Practitioner, Bed, Patient, PatientResidence, Kinship, Encounter,
    BedOccupancy, Procedure, DiagnosticReport, Observation, Payer,
    Invoice, InvoiceLine, Appointment, Referral, CodeAct, CodeDiagICD10, CodeLabLOINC, VisitType
)

# --------- Mixins ---------
class TenantAwareMixin:
    """
    Vérifie la cohérence des FKs pointant vers un facility du même tenant (si applicable).
    L’auto-remplissage du tenant_key est fait dans les modèles. Ici on fait une validation app.
    """
    def validate(self, attrs):
        # On essaie de repérer un facility direct
        facility = attrs.get("facility") or getattr(self.instance, "facility", None)
        # ou via encounter
        enc = attrs.get("encounter") or getattr(self.instance, "encounter", None)
        if not facility and enc:
            facility = enc.facility
        # ou via bed
        bed = attrs.get("bed") or getattr(self.instance, "bed", None)
        if not facility and bed:
            facility = bed.facility

        # tenant_key du payload (si présent) — normalement non éditable
        tenant_key = attrs.get("tenant_key") or getattr(self.instance, "tenant_key", None)

        if facility and tenant_key and tenant_key != facility.root().code:
            raise serializers.ValidationError("tenant_key inconsistent with facility root code.")

        return super().validate(attrs)


# --------- Basic / Reference Serializers ---------
class PoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pole
        fields = "__all__"

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = "__all__"

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = "__all__"

class CommuneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commune
        fields = "__all__"

class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = "__all__"

class DepartmentSerializer(serializers.ModelSerializer, TenantAwareMixin):
    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ("tenant_key",)

class PractitionerSerializer(serializers.ModelSerializer, TenantAwareMixin):
    class Meta:
        model = Practitioner
        fields = "__all__"
        read_only_fields = ("tenant_key",)

class BedSerializer(serializers.ModelSerializer, TenantAwareMixin):
    class Meta:
        model = Bed
        fields = "__all__"
        read_only_fields = ("tenant_key",)

class PayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payer
        fields = "__all__"

# --------- Patient Domain ---------
class PatientResidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientResidence
        fields = "__all__"

class PatientSerializer(serializers.ModelSerializer):
    residences = PatientResidenceSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = "__all__"

class KinshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kinship
        fields = "__all__"

# --------- Clinical ---------
class VisitTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitType
        fields = "__all__"

class EncounterSerializer(serializers.ModelSerializer, TenantAwareMixin):
    visit_type_code = serializers.SlugRelatedField(
        source="visit_type",
        slug_field="code",
        queryset=VisitType.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Encounter
        fields = "__all__"
        read_only_fields = ("tenant_key",)

class BedOccupancySerializer(serializers.ModelSerializer, TenantAwareMixin):
    class Meta:
        model = BedOccupancy
        fields = "__all__"
        read_only_fields = ("tenant_key",)

class ProcedureSerializer(serializers.ModelSerializer, TenantAwareMixin):
    class Meta:
        model = Procedure
        fields = "__all__"
        read_only_fields = ("tenant_key",)

class DiagnosticReportSerializer(serializers.ModelSerializer, TenantAwareMixin):
    class Meta:
        model = DiagnosticReport
        fields = "__all__"
        read_only_fields = ("tenant_key",)

class ObservationSerializer(serializers.ModelSerializer, TenantAwareMixin):
    class Meta:
        model = Observation
        fields = "__all__"
        read_only_fields = ("tenant_key",)

# --------- Billing ---------
class InvoiceLineSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceLine
        fields = ("id", "invoice", "act_code", "label", "qty", "unit_price", "amount")

    def get_amount(self, obj):
        return obj.qty * obj.unit_price

class InvoiceSerializer(serializers.ModelSerializer, TenantAwareMixin):
    lines = InvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ("tenant_key",)

# --------- Appointments / Referrals ---------
class AppointmentSerializer(serializers.ModelSerializer, TenantAwareMixin):
    class Meta:
        model = Appointment
        fields = "__all__"
        read_only_fields = ("tenant_key",)

class ReferralSerializer(serializers.ModelSerializer, TenantAwareMixin):
    class Meta:
        model = Referral
        fields = "__all__"
        read_only_fields = ("tenant_key",)

# --------- Code Systems (read-only) ---------
class CodeActSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodeAct
        fields = "__all__"

class CodeICD10Serializer(serializers.ModelSerializer):
    class Meta:
        model = CodeDiagICD10
        fields = "__all__"

class CodeLOINCSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodeLabLOINC
        fields = "__all__"

# --------- Users ---------
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"