import django_filters as df
from hospital.models import Encounter, Appointment, Observation, Invoice, VisitType


class EncounterFilter(df.FilterSet):
    start_after = df.IsoDateTimeFilter(field_name="start_at", lookup_expr="gte")
    start_before = df.IsoDateTimeFilter(field_name="start_at", lookup_expr="lte")
    visit_type = df.ModelChoiceFilter(field_name="visit_type", queryset=VisitType.objects.all())
    visit_type_code = df.CharFilter(field_name="visit_type__code", lookup_expr="iexact")  # pratique

    patient = df.UUIDFilter(field_name="patient__id")
    facility = df.UUIDFilter(field_name="facility__id")

    class Meta:
        model = Encounter
        fields = ["visit_type", "visit_type_code", "patient", "facility"]


class AppointmentFilter(df.FilterSet):
    start_after = df.IsoDateTimeFilter(field_name="start_at", lookup_expr="gte")
    start_before = df.IsoDateTimeFilter(field_name="start_at", lookup_expr="lte")
    status = df.CharFilter(lookup_expr="iexact")
    practitioner = df.UUIDFilter(field_name="practitioner__id")
    patient = df.UUIDFilter(field_name="patient__id")
    class Meta:
        model = Appointment
        fields = ["status", "practitioner", "patient"]

class ObservationFilter(df.FilterSet):
    observed_after = df.IsoDateTimeFilter(field_name="observed_at", lookup_expr="gte")
    observed_before = df.IsoDateTimeFilter(field_name="observed_at", lookup_expr="lte")
    loinc_code = df.CharFilter(lookup_expr="iexact")
    encounter = df.UUIDFilter(field_name="encounter__id")
    class Meta:
        model = Observation
        fields = ["loinc_code", "encounter"]

class InvoiceFilter(df.FilterSet):
    issued_after = df.IsoDateTimeFilter(field_name="issued_at", lookup_expr="gte")
    issued_before = df.IsoDateTimeFilter(field_name="issued_at", lookup_expr="lte")
    status = df.CharFilter(lookup_expr="iexact")
    encounter = df.UUIDFilter(field_name="encounter__id")
    class Meta:
        model = Invoice
        fields = ["status", "encounter"]