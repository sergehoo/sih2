from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserProfileViewSet, PoleViewSet, RegionViewSet, DistrictViewSet, CommuneViewSet,

    PatientViewSet, PatientResidenceViewSet, KinshipViewSet,
    CodeActViewSet, CodeICD10ViewSet, CodeLOINCViewSet,
    MyEncountersViewSet, MyObservationsViewSet, MyInvoicesViewSet,
)

router = DefaultRouter()
# Référentiels géo & établissements
router.register(r"poles", PoleViewSet, basename="pole")
router.register(r"regions", RegionViewSet, basename="region")
router.register(r"districts", DistrictViewSet, basename="district")
router.register(r"communes", CommuneViewSet, basename="commune")

# Patient
router.register(r"patients", PatientViewSet, basename="patient")
router.register(r"patient-residences", PatientResidenceViewSet, basename="patient-residence")
router.register(r"kinships", KinshipViewSet, basename="kinship")

# Code systems (read-only)
router.register(r"codes/act", CodeActViewSet, basename="code-act")
router.register(r"codes/icd10", CodeICD10ViewSet, basename="code-icd10")
router.register(r"codes/loinc", CodeLOINCViewSet, basename="code-loinc")

# /me endpoints (portail patient)
me_router = DefaultRouter()
me_router.register(r"encounters", MyEncountersViewSet, basename="me-encounters")
me_router.register(r"observations", MyObservationsViewSet, basename="me-observations")
me_router.register(r"invoices", MyInvoicesViewSet, basename="me-invoices")


urlpatterns = [
    path("v1/", include(router.urls)),
    path("v1/me/", include(me_router.urls)),
]
