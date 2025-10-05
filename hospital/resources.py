# hospital/resources.py
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, Widget
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from .models import Pole, Region, District


# -- Widget pour Region en s'appuyant sur le nom du Pôle + nom Région --
class RegionByPoleAndNameWidget(ForeignKeyWidget):
    """
    Colonne 'region' = nom de la région,
    Colonne 'pole'   = nom du pôle (pour désambiguïser)
    """

    def __init__(self, model, field="name"):
        super().__init__(model, field)

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None
        pole_name = (row.get("pole") or row.get("Pole") or "").strip()
        qs = self.model.objects
        try:
            if pole_name:
                return qs.get(name=value, pole__name=pole_name)
            return qs.get(name=value)
        except ObjectDoesNotExist:
            raise ValueError(
                _(f"Région introuvable: '{value}' (pôle='{pole_name or '—'}').")
            )

    def render(self, obj, *args, **kwargs):
        return getattr(obj, "name", "") if obj else ""


# -- Widget simple pour géométrie (WKT) --
try:
    from django.contrib.gis.geos import GEOSGeometry
except Exception:
    GEOSGeometry = None


class WKTGeometryWidget(Widget):
    """
    Sérialise MultiPolygon/Polygon en WKT pour CSV/Excel.
    À l'import, accepte WKT (et SRID=4326 par défaut si absent).
    """
    default_srid = 4326

    def clean(self, value, row=None, *args, **kwargs):
        if not value or not GEOSGeometry:
            return None
        geom = GEOSGeometry(value)
        if not geom.srid:
            geom.srid = self.default_srid
        return geom

    def render(self, value, obj=None):
        if not value or not GEOSGeometry:
            return ""
        try:
            return value.wkt  # texte WKT
        except Exception:
            return ""


# =========================
#   Resources
# =========================

class PoleResource(resources.ModelResource):
    id = fields.Field(attribute="id", column_name="id")
    name = fields.Field(attribute="name", column_name="name")

    class Meta:
        model = Pole
        fields = ("id", "name", "created", "modified")
        export_order = ("id", "name", "created", "modified")
        skip_unchanged = True
        report_skipped = True


class RegionResource(resources.ModelResource):
    id = fields.Field(attribute="id", column_name="id")
    pole = fields.Field(
        attribute="pole",
        column_name="pole",
        widget=ForeignKeyWidget(Pole, "name"),
    )
    name = fields.Field(attribute="name", column_name="name")

    class Meta:
        model = Region
        fields = ("id", "pole", "name", "created", "modified")
        export_order = ("id", "pole", "name", "created", "modified")
        skip_unchanged = True
        report_skipped = True
        # unique_together géré côté modèle; import-export fera update si id matche.


class DistrictResource(resources.ModelResource):
    id = fields.Field(attribute="id", column_name="id")
    pole = fields.Field(
        column_name="pole",
        readonly=True,  # calculé à l'export via dehydrate_pole
    )
    region = fields.Field(
        attribute="region",
        column_name="region",
        widget=RegionByPoleAndNameWidget(Region, "name"),
    )
    name = fields.Field(attribute="name", column_name="name")
    geom = fields.Field(attribute="geom", column_name="geom_wkt", widget=WKTGeometryWidget())

    class Meta:
        model = District
        fields = ("id", "pole", "region", "name", "geom", "created", "modified")
        export_order = ("id", "pole", "region", "name", "geom", "created", "modified")
        skip_unchanged = True
        report_skipped = True

    def dehydrate_pole(self, obj):
        return getattr(getattr(obj, "region", None), "pole", None) or ""
