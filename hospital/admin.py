from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from .models import (
    UserProfile, Pole, Region, District, Commune, Facility, Department,
    Practitioner, Bed, Patient, PatientResidence, Kinship, Encounter,
    BedOccupancy, Procedure, DiagnosticReport, Observation, Payer,
    Invoice, InvoiceLine, Appointment, Referral, CodeAct, CodeDiagICD10, CodeLabLOINC, VisitType
)

admin.site.site_header = 'BACK-END SIGH'
admin.site.site_title = 'MSHPCMU Admin Pannel'
admin.site.site_url = 'http://mshpcmu.com/'
admin.site.index_title = 'MSHPCMU '
admin.empty_value_display = '**Empty**'
# -------- Inlines --------
class PatientResidenceInline(admin.TabularInline):
    model = PatientResidence
    extra = 0
    fields = ("commune", "address_text", "from_date", "to_date", "is_primary")
    show_change_link = True


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    fields = ("act_code", "label", "qty", "unit_price")
    readonly_fields = ()
    show_change_link = False


# -------- Geo Admin --------
@admin.register(District)
class DistrictAdmin(OSMGeoAdmin):
    list_display = ("name", "region")
    list_filter = ("region",)
    search_fields = ("name", "region__name")
    default_lon = 0
    default_lat = 0
    default_zoom = 6


@admin.register(Commune)
class CommuneAdmin(OSMGeoAdmin):
    list_display = ("name", "district")
    list_filter = ("district",)
    search_fields = ("name", "district__name")
    default_lon = 0
    default_lat = 0
    default_zoom = 7


@admin.register(Facility)
class FacilityAdmin(OSMGeoAdmin):
    list_display = ("name", "code", "type", "is_chu", "active", "parent")
    list_filter = ("type", "is_chu", "active", "region", "district", "commune")
    search_fields = ("name", "code")
    raw_id_fields = ("parent", "region", "district", "commune")
    default_lon = 0
    default_lat = 0
    default_zoom = 7


# -------- Référentiels simples --------
@admin.register(Pole)
class PoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "pole")
    list_filter = ("pole",)
    search_fields = ("name", "pole__name")


# -------- Hôpital --------
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "facility", "type", "tenant_key")
    list_filter = ("type", "facility")
    search_fields = ("name", "code", "facility__name", "facility__code")
    raw_id_fields = ("facility",)
    readonly_fields = ("tenant_key",)


@admin.register(Practitioner)
class PractitionerAdmin(admin.ModelAdmin):
    list_display = ("matricule", "role", "specialty", "facility", "department", "active", "tenant_key")
    list_filter = ("role", "active", "facility")
    search_fields = ("matricule", "specialty", "facility__code", "department__name")
    raw_id_fields = ("facility", "department")
    readonly_fields = ("tenant_key",)


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ("code", "facility", "department", "active", "tenant_key")
    list_filter = ("active", "facility", "department")
    search_fields = ("code", "facility__code", "department__name")
    raw_id_fields = ("facility", "department")
    readonly_fields = ("tenant_key",)


# -------- Patient & famille --------
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("mpi", "family_name", "given_name", "birth_date", "is_deceased", "death_date", "residence_commune")
    list_filter = ("is_deceased", "residence_commune")
    search_fields = ("mpi", "family_name", "given_name")
    inlines = [PatientResidenceInline]
    raw_id_fields = ("residence_commune", "father", "mother")


@admin.register(Kinship)
class KinshipAdmin(admin.ModelAdmin):
    list_display = ("src", "relation", "dst", "valid_from", "valid_to")
    list_filter = ("relation",)
    search_fields = ("src__mpi", "dst__mpi")


@admin.register(PatientResidence)
class PatientResidenceAdmin(admin.ModelAdmin):
    list_display = ("patient", "commune", "from_date", "to_date", "is_primary")
    list_filter = ("is_primary", "commune")
    search_fields = ("patient__mpi", "commune__name")
    raw_id_fields = ("patient", "commune")


# -------- Clinique --------
@admin.register(VisitType)
class VisitTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "category", "active", "sort_order")
    list_filter  = ("active", "category")
    search_fields = ("code", "label")
    ordering = ("sort_order", "code")

@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "facility", "department", "visit_type", "start_at", "end_at", "tenant_key")
    list_filter = ("visit_type", "facility", "department")
    search_fields = ("patient__mpi", "facility__code")
    raw_id_fields = ("patient", "facility", "department")
    readonly_fields = ("tenant_key",)


@admin.register(BedOccupancy)
class BedOccupancyAdmin(admin.ModelAdmin):
    list_display = ("bed", "patient", "from_ts", "to_ts", "status", "tenant_key")
    list_filter = ("status",)
    search_fields = ("bed__code", "patient__mpi")
    raw_id_fields = ("bed", "patient")
    readonly_fields = ("tenant_key",)


@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "encounter", "performed_at", "performer", "tenant_key")
    list_filter = ("performed_at",)
    search_fields = ("code", "name", "encounter__patient__mpi")
    raw_id_fields = ("encounter", "performer")
    readonly_fields = ("tenant_key",)


@admin.register(DiagnosticReport)
class DiagnosticReportAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "modality", "status", "issued_at", "tenant_key")
    list_filter = ("modality", "status")
    search_fields = ("encounter__patient__mpi",)
    raw_id_fields = ("encounter",)
    readonly_fields = ("tenant_key",)


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ("loinc_code", "encounter", "observed_at", "result_flag", "tenant_key")
    list_filter = ("result_flag",)
    search_fields = ("loinc_code", "encounter__patient__mpi")
    raw_id_fields = ("encounter", "report")
    readonly_fields = ("tenant_key",)


# -------- Facturation --------
@admin.register(Payer)
class PayerAdmin(admin.ModelAdmin):
    list_display = ("code", "label")
    search_fields = ("code", "label")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "payer", "status", "total", "issued_at", "tenant_key")
    list_filter = ("status", "issued_at")
    search_fields = ("encounter__patient__mpi", "payer__code")
    inlines = [InvoiceLineInline]
    raw_id_fields = ("encounter", "payer")
    readonly_fields = ("tenant_key",)


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "act_code", "label", "qty", "unit_price")
    search_fields = ("invoice__id", "act_code", "label")
    raw_id_fields = ("invoice",)


# -------- RDV & Références --------
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "practitioner", "facility", "department", "start_at", "end_at", "status", "tenant_key")
    list_filter = ("status", "facility", "department")
    search_fields = ("patient__mpi", "practitioner__matricule", "facility__code")
    raw_id_fields = ("patient", "practitioner", "facility", "department")
    readonly_fields = ("tenant_key",)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("from_facility", "to_facility", "patient", "status", "tenant_key", "created_at")
    list_filter = ("status", "from_facility", "to_facility")
    search_fields = ("patient__mpi", "from_facility__code", "to_facility__code")
    raw_id_fields = ("from_facility", "to_facility", "patient")
    readonly_fields = ("tenant_key",)


# -------- Codes (lecture seule) --------
@admin.register(CodeAct)
class CodeActAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "category")
    search_fields = ("code", "label", "category")
    readonly_fields = ()


@admin.register(CodeDiagICD10)
class CodeDiagICD10Admin(admin.ModelAdmin):
    list_display = ("icd10", "label")
    search_fields = ("icd10", "label")


@admin.register(CodeLabLOINC)
class CodeLabLOINCAdmin(admin.ModelAdmin):
    list_display = ("loinc", "label")
    search_fields = ("loinc", "label")


# -------- Profils utilisateurs --------
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("username", "idp_sub", "facility", "tenant_key", "scope_level")
    list_filter = ("scope_level", "facility")
    search_fields = ("username", "idp_sub", "tenant_key")
    raw_id_fields = ("facility",)
