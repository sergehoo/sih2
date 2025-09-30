# pharmacy/models.py
from django.db import models
from core.models.base import UUIDModel, TimeStampedModel, TenantScopedModel
from geo.models import Facility

class Drug(UUIDModel, TimeStampedModel):
    atc_code = models.CharField(max_length=32, db_index=True)
    label = models.CharField(max_length=255)
    form = models.CharField(max_length=64, null=True, blank=True)
    strength = models.CharField(max_length=64, null=True, blank=True)
    class Meta:
        unique_together = ("atc_code","label")

class InventoryItem(UUIDModel, TimeStampedModel, TenantScopedModel):
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT)
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT)
    sku = models.CharField(max_length=64, db_index=True)            # code interne
    min_threshold = models.IntegerField(default=0)
    class Meta:
        unique_together = ("facility","sku")

class InventoryLot(UUIDModel, TimeStampedModel, TenantScopedModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="lots")
    lot_code = models.CharField(max_length=64)
    expiration = models.DateField(null=True, blank=True)
    quantity = models.IntegerField(default=0)
    class Meta:
        unique_together = ("item","lot_code")

class InventoryMovement(UUIDModel, TimeStampedModel, TenantScopedModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    lot = models.ForeignKey(InventoryLot, null=True, blank=True, on_delete=models.SET_NULL)
    movement_type = models.CharField(max_length=16)   # IN, OUT, ADJUST
    qty = models.IntegerField()
    at = models.DateTimeField(db_index=True)
    reason = models.CharField(max_length=128, null=True, blank=True)
    class Meta:
        indexes = [models.Index(fields=["tenant_key","at","movement_type"])]