from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import AppointmentViewSet
from finances.views import InvoiceViewSet, InvoiceLineViewSet, PayerViewSet
from hospital.api.views import ReferralViewSet

router = DefaultRouter()

# Facturation & RDV
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"invoice-lines", InvoiceLineViewSet, basename="invoice-line")
router.register(r"appointments", AppointmentViewSet, basename="appointment")
router.register(r"referrals", ReferralViewSet, basename="referral")
router.register(r"payers", PayerViewSet, basename="payer")


urlpatterns = [
    path("", include(router.urls)),  # <= expose bien des patterns
]