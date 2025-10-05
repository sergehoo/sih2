from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django import forms
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import (
    UserProfile, Pole, Region, District, Commune, Facility, Department,
    Practitioner, Bed, Patient, PatientResidence, Kinship, Encounter,
    BedOccupancy, Procedure, DiagnosticReport, Observation, Payer,
    Invoice, InvoiceLine, Appointment, Referral, CodeAct, CodeDiagICD10, CodeLabLOINC, VisitType, ScopeLevel
)

admin.site.site_header = 'BACK-END SIGH'
admin.site.site_title = 'MSHPCMU Admin Pannel'
admin.site.site_url = 'http://mshpcmu.com/'
admin.site.index_title = 'MSHPCMU '
admin.empty_value_display = '**Empty**'


# -------- Inlines --------


# ---------- Forme d'édition : champs CSV -> ArrayField ----------
class UserProfileAdminForm(forms.ModelForm):
    departments_csv = forms.CharField(
        required=False,
        label=_("Départements (CSV)"),
        help_text=_("Ex.: chirurgie,labo,cardiologie"),
        widget=admin.widgets.AdminTextInputWidget,
    )
    roles_csv = forms.CharField(
        required=False,
        label=_("Rôles (CSV)"),
        help_text=_("Ex.: ROLE_MEDECIN,ROLE_PATIENT"),
        widget=admin.widgets.AdminTextInputWidget,
    )

    class Meta:
        model = UserProfile
        fields = "__all__"
        exclude = ("departments", "roles")  # on garde bien exclus

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inst = self.instance
        if inst and inst.pk:
            # initial depuis la liste -> CSV visible
            self.fields["departments_csv"].initial = ",".join(inst.departments or [])
            self.fields["roles_csv"].initial = ",".join(inst.roles or [])

    def _to_list(self, value):
        """Accepte string CSV, liste/tuple, None -> renvoie liste normalisée."""
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            items = [str(x).strip() for x in value if str(x).strip()]
        else:
            # value est une string
            items = [x.strip() for x in str(value).split(",") if x.strip()]
        return items

    def clean_departments_csv(self):
        raw = self.cleaned_data.get("departments_csv", "")
        # normalisation : lower pour les codes de dept
        return [i.lower() for i in self._to_list(raw)]

    def clean_roles_csv(self):
        raw = self.cleaned_data.get("roles_csv", "")
        # ici on garde la casse (ROLE_*)
        return self._to_list(raw)

    def save(self, commit=True):
        inst = super().save(commit=False)
        # récupère le résultat des cleaners (toujours listes Python)
        inst.departments = self.cleaned_data.get("departments_csv", []) or []
        inst.roles = self.cleaned_data.get("roles_csv", []) or []
        if commit:
            inst.save()
            self.save_m2m()
        return inst


# ---------- Filtres de liste pour ArrayField ----------
class RoleListFilter(admin.SimpleListFilter):
    title = _("Rôle")
    parameter_name = "role"

    # valeurs proposées (adapte selon ton référentiel)
    def lookups(self, request, model_admin):
        return (
            ("ROLE_DIRECTEUR_ETABLISSEMENT", _("Directeur d’établissement")),
            ("ROLE_MEDECIN", _("Médecin")),
            ("ROLE_INFIRMIER", _("Infirmier(ère)")),
            ("ROLE_ADMIN", _("Admin")),
            ("ROLE_PATIENT", _("Patient")),
        )

    def queryset(self, request, qs):
        val = self.value()
        if val:
            return qs.filter(roles__contains=[val])
        return qs


class DepartmentListFilter(admin.SimpleListFilter):
    title = _("Département")
    parameter_name = "dept"

    def lookups(self, request, model_admin):
        """
        Construit la liste des 20 départements les plus fréquents en lisant
        les valeurs Python (listes) sans faire de filtre SQL du type departments=[]
        (source de cast foireux jsonb ↔ varchar[]).
        """
        qs = model_admin.get_queryset(request).only("departments")
        bucket = {}
        for arr in qs.values_list("departments", flat=True):
            if isinstance(arr, (list, tuple)):
                for d in arr:
                    if not d:
                        continue
                    k = str(d).lower()
                    bucket[k] = bucket.get(k, 0) + 1
        top = sorted(bucket.items(), key=lambda x: -x[1])[:20]
        return [(k, k.title()) for k, _ in top] or [("—", "—")]

    def queryset(self, request, qs):
        val = self.value()
        if not val or val == "—":
            return qs
        # Compatible JSONField (jsonb) ET ArrayField : utilise l'opérateur @> ou array-contains.
        return qs.filter(departments__contains=[val])


# ---------- Admin ----------
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm

    list_display = (
        "username",
        "email",
        "tenant_key",
        "facility",
        "scope_badge",
        "roles_display",
        "departments_display",

    )
    list_select_related = ("facility",)
    ordering = ("username",)
    # date_hierarchy = "created"

    # recherche & filtres
    search_fields = ("username", "email", "phone", "idp_sub", "patient_mpi")
    list_filter = (
        "tenant_key",
        "scope_level",
        RoleListFilter,
        DepartmentListFilter,
    )

    autocomplete_fields = ("facility",)

    # readonly_fields = ("idp_sub", "classified")

    fieldsets = (
        (_("Identité & rattachements"), {
            "fields": (
                ("username", "email"),
                ("phone",),
                ("facility", "tenant_key"),
                ("idp_sub",),
            )
        }),
        (_("Accès / Portée"), {
            "fields": ("scope_level",),
        }),
        (_("Rôles & Départements"), {
            "fields": ("roles_csv", "departments_csv"),
            "description": _(
                "Renseignez des valeurs séparées par des virgules. "
                "Ex. Rôles: <code>ROLE_MEDECIN,ROLE_DIRECTION</code> — "
                "Départements: <code>cardiologie,labo</code>"
            ),
        }),
        (_("Lien Patient"), {
            "fields": ("patient_mpi",),
        }),

    )

    # -- colonnes jolies --
    @admin.display(description=_("Portée"), ordering="scope_level")
    def scope_badge(self, obj: UserProfile):
        color = {
            ScopeLevel.SERVICE: "#10b981",  # emerald
            ScopeLevel.DISTRICT: "#3b82f6",  # blue
            ScopeLevel.REGION: "#8b5cf6",  # violet
            ScopeLevel.POLE: "#f59e0b",  # amber
            ScopeLevel.NATIONAL: "#ef4444",  # red
        }.get(obj.scope_level, "#6b7280")  # gray
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:9999px;'
            'background:rgba(0,0,0,0.04);color:{};font-weight:600;">{}</span>',
            color,
            obj.get_scope_level_display(),
        )

    @admin.display(description=_("Rôles"))
    def roles_display(self, obj: UserProfile):
        return ", ".join(obj.roles or [])

    @admin.display(description=_("Départements"))
    def departments_display(self, obj: UserProfile):
        return ", ".join(obj.departments or [])

    # Actions utiles (exemples)
    actions = ["clear_roles", "clear_departments"]

    @admin.action(description=_("Vider les rôles sélectionnés"))
    def clear_roles(self, request, queryset):
        updated = queryset.update(roles=[])
        self.message_user(request, _("%d profils mis à jour (rôles vidés).") % updated)

    @admin.action(description=_("Vider les départements sélectionnés"))
    def clear_departments(self, request, queryset):
        updated = queryset.update(departments=[])
        self.message_user(request, _("%d profils mis à jour (départements vidés).") % updated)


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
class DistrictAdmin(ImportExportModelAdmin):
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
    list_filter = ("type", "is_chu", "active", "commune")
    search_fields = ("name", "code")
    raw_id_fields = ("parent", "commune")
    default_lon = 0
    default_lat = 0
    default_zoom = 7


# -------- Référentiels simples --------
@admin.register(Pole)
class PoleAdmin(ImportExportModelAdmin):
    list_display = ("id", "name",)
    search_fields = ("name",)


class RegionResource(resources.ModelResource):
    # on lit une colonne "pole" dans le fichier d'import,
    # et on la mappe au champ FK "pole" via le nom du pôle.
    poles = fields.Field(
        column_name="pole",
        attribute="pole",
        widget=ForeignKeyWidget(Pole, "name"),
    )

    class Meta:
        model = Region
        import_id_fields = ("name",)  # ou ("name","pole") si tu veux l’unicité par couple
        fields = ("id", "name", "pole",)  # colonnes autorisées à l’import/export
        skip_unchanged = True


@admin.register(Region)
class RegionAdmin(ImportExportModelAdmin):
    list_display = ("name", "poles")
    list_filter = ("poles",)
    search_fields = ("name", "poles__name")
    # resource_class = RegionResource


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
    list_filter = ("active", "category")
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
    list_select_related = ("encounter", "encounter__patient", "encounter__facility")


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
# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ("username", "idp_sub", "facility", "tenant_key", "scope_level")
#     list_filter = ("scope_level", "facility")
#     search_fields = ("username", "idp_sub", "tenant_key")
#     raw_id_fields = ("facility",)
