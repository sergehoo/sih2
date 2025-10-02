#/Users/ogahserge/Documents/sigh/hospital/base.py
import uuid
from django.db import models
# core/models/base.py
import uuid
from django.db import models
from django.core.exceptions import ValidationError


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class TenantScopedModel(models.Model):
    """
    Mixin pour 'scoper' un enregistrement par établissement (facility).
    - Remplit automatiquement tenant_key à partir de <TENANT_FK_FIELD>.code (par défaut 'facility')
    - Empêche l'édition manuelle de tenant_key
    - Valide la cohérence à l'enregistrement
    """
    tenant_key = models.CharField(max_length=64, db_index=True, editable=False)

    # Si un modèle utilise un autre nom de FK (ex: 'hospital'), override cette constante:
    # TENANT_FK_FIELD = "hospital"
    TENANT_FK_FIELD = "facility"

    class Meta:
        abstract = True

    def _derive_tenant_key(self):
        fk_name = getattr(self, "TENANT_FK_FIELD", "facility")
        fac = getattr(self, fk_name, None)
        if fac is not None:
            root = fac.root() if hasattr(fac, "root") else fac
            if getattr(root, "code", None):
                self.tenant_key = root.code

    def clean(self):
        # Assure le remplissage avant validation et lève une erreur si impossible
        self._derive_tenant_key()
        if not self.tenant_key:
            raise ValidationError(
                "tenant_key n'a pas pu être dérivé : vérifie que la FK 'facility' "
                "(ou TENANT_FK_FIELD) est renseignée et que Facility.code est défini."
            )

    def save(self, *args, **kwargs):
        self._derive_tenant_key()
        super().save(*args, **kwargs)
