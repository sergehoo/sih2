from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import InvoiceFilter
from api.permissions import IsStaff
from api.serializers import InvoiceSerializer, InvoiceLineSerializer, PayerSerializer
from api.views import DefaultsMixin
from hospital.models import Invoice, InvoiceLine, Payer


# Create your views here.
# ------------- Billing -------------
class InvoiceViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("encounter", "payer").all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsStaff]
    filterset_class = InvoiceFilter
    search_fields = ("status", "encounter__patient__mpi")
    ordering = ("-issued_at", "-created_at")

    @action(detail=True, methods=["post"], url_path="issue")
    def issue(self, request, pk=None):
        obj = self.get_object()
        if obj.status not in ("DRAFT",):
            return Response({"detail": "Invoice already issued or closed."}, status=400)
        obj.status = "ISSUED"
        obj.issued_at = obj.issued_at or timezone.now()
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"], url_path="pay")
    def pay(self, request, pk=None):
        obj = self.get_object()
        if obj.status not in ("ISSUED",):
            return Response({"detail": "Invoice not in ISSUED state."}, status=400)
        obj.status = "PAID"
        obj.save()
        return Response(self.get_serializer(obj).data)


class InvoiceLineViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = InvoiceLine.objects.select_related("invoice").all()
    serializer_class = InvoiceLineSerializer
    permission_classes = [IsStaff]
    search_fields = ("act_code", "label")


class PayerViewSet(DefaultsMixin, viewsets.ModelViewSet):
    queryset = Payer.objects.all().order_by("code")
    serializer_class = PayerSerializer
    permission_classes = [IsStaff]
    search_fields = ("code", "label")
