from django.urls import include, path
from rest_framework.routers import DefaultRouter

from hospital.api.views import EncounterViewSet, BedOccupancyViewSet, ProcedureViewSet, DiagnosticReportViewSet, \
    ObservationViewSet, FacilityViewSet, DepartmentViewSet, PractitionerViewSet, BedViewSet, VisitTypeViewSet

router = DefaultRouter()

# Clinique
router.register(r"encounters", EncounterViewSet, basename="encounter")
router.register(r"bed-occupancies", BedOccupancyViewSet, basename="bed-occupancy")
router.register(r"procedures", ProcedureViewSet, basename="procedure")
router.register(r"diagnostic-reports", DiagnosticReportViewSet, basename="diagnostic-report")
router.register(r"observations", ObservationViewSet, basename="observation")
router.register(r"facilities", FacilityViewSet, basename="facility")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"practitioners", PractitionerViewSet, basename="practitioner")
router.register(r"beds", BedViewSet, basename="bed")
router.register(r"visit-types", VisitTypeViewSet, basename="visit-type")




urlpatterns = [
    path("", include(router.urls)),  # <= expose bien des patterns
]