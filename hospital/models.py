# /Users/ogahserge/Documents/sigh/hospital/models.py
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from django.db import models
from django.utils import timezone
from .base import UUIDModel, TimeStampedModel
from django.contrib.gis.db import models as gmodels
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.indexes import GistIndex

from .base import TenantScopedModel


class UserProfile(UUIDModel, TimeStampedModel):
    # "sub" Keycloak (ou autre IdP)
    facility = models.ForeignKey('Facility', null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="users")  # +++
    idp_sub = models.CharField(max_length=128, unique=True, db_index=True)
    username = models.CharField(max_length=150, db_index=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)

    # Attributs d’accès (ABAC)
    tenant_key = models.CharField(max_length=64, null=True, blank=True)  # CHU personnel
    scope_level = models.CharField(max_length=20, default='SERVICE')  # SERVICE/DISTRICT/REGION/POLE/NATIONAL
    departments = models.JSONField(default=list, blank=True)  # ["chirurgie","labo"]

    # Lien vers Patient (si compte patient)
    patient_mpi = models.CharField(max_length=128, null=True, blank=True)  # identifiant MPI pseudonymisé

    # Rôles (copie utile pour filtrages rapides côté app, la vérité vient du JWT)
    roles = models.JSONField(default=list, blank=True)  # ["ROLE_MEDECIN","ROLE_PATIENT",...]

    class Meta:
        verbose_name = _("Profil utilisateur")
        verbose_name_plural = _("Profils utilisateurs")
        indexes = [
            models.Index(fields=["tenant_key", "scope_level"]),
            models.Index(fields=["username"]),
        ]


class Pole(UUIDModel, TimeStampedModel):
    name = gmodels.CharField(max_length=128, unique=True)

    class Meta:
        verbose_name = _("Pôle régional")
        verbose_name_plural = _("Pôles régionaux")


class Region(UUIDModel, TimeStampedModel):
    pole = gmodels.ForeignKey(Pole, on_delete=gmodels.PROTECT, related_name="regions")
    name = gmodels.CharField(max_length=128)

    class Meta:
        verbose_name = _("Région sanitaire")
        verbose_name_plural = _("Régions sanitaires")
        unique_together = ("pole", "name")


class District(UUIDModel, TimeStampedModel):
    region = gmodels.ForeignKey(Region, on_delete=gmodels.PROTECT, related_name="districts")
    name = gmodels.CharField(max_length=128)
    geom = gmodels.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        verbose_name = _("District sanitaire")
        verbose_name_plural = _("Districts sanitaires")
        unique_together = ("region", "name")


class Commune(UUIDModel, TimeStampedModel):
    district = gmodels.ForeignKey(District, on_delete=gmodels.PROTECT, related_name="communes")
    name = gmodels.CharField(max_length=128)
    geom = gmodels.MultiPolygonField(srid=4326, null=True, blank=True)
    centroid = gmodels.PointField(srid=4326, null=True, blank=True)

    class Meta:
        verbose_name = _("Commune")
        verbose_name_plural = _("Communes")
        unique_together = ("district", "name")


class Facility(UUIDModel, TimeStampedModel):
    code = gmodels.CharField(max_length=46,default=uuid.uuid4, unique=True, db_index=True)  # Code unique (MSHP, interne…)
    name = gmodels.CharField(max_length=255)  # Nom de l’hôpital
    is_chu = gmodels.BooleanField(default=False)  # True si CHU
    type = gmodels.CharField(  # Type d’établissement
        max_length=32,
        choices=[
            ("CHU", "Centre Hospitalier Universitaire"),
            ("CHR", "Centre Hospitalier Régional"),
            ("HOSPITAL", "Hôpital Général"),
            ("CS", "Centre de Santé"),
            ("LAB", "Laboratoire"),
            ("PHARMA", "Pharmacie"),
        ],
        default="HOSPITAL",
    )
    active = gmodels.BooleanField(default=True)
    parent = gmodels.ForeignKey("self", null=True, blank=True, on_delete=gmodels.PROTECT, related_name="children")
    # Localisation & rattachements
    location = gmodels.PointField(srid=4326, null=True, blank=True)
    commune = gmodels.ForeignKey("Commune", on_delete=gmodels.PROTECT, null=True, blank=True)
    district = gmodels.ForeignKey("District", on_delete=gmodels.PROTECT, null=True, blank=True)
    region = gmodels.ForeignKey("Region", on_delete=gmodels.PROTECT, null=True, blank=True)

    def root(self):
        n = self
        while n.parent_id:
            n = n.parent
        return n

    class Meta:
        verbose_name = _("Établissement de santé")
        verbose_name_plural = _("Établissements de santé")
        indexes = [
            gmodels.Index(fields=["code"]),  # redondant avec unique mais ok
            gmodels.Index(fields=["type"]),
            gmodels.Index(fields=["active"]),
            gmodels.Index(fields=["parent"]),
            gmodels.Index(fields=["region"]),
            gmodels.Index(fields=["district"]),
            gmodels.Index(fields=["commune"]),
            gmodels.Index(fields=["name"]),
            GistIndex(fields=["location"]),  # <— index spatial GIST
        ]
        # Exemple de contrainte logique simple
        constraints = [
            gmodels.CheckConstraint(
                check=~gmodels.Q(is_chu=True) | gmodels.Q(type="CHU"),
                name="facility_chu_implies_type_chu",
            ),
            gmodels.CheckConstraint(
                check=~gmodels.Q(parent=models.F("id")),
                name="facility_parent_not_self",
            ),
        ]

    def clean(self):
        # Cohérence métier : si CHU, le type doit être CHU
        if self.is_chu and self.type != "CHU":
            raise ValidationError("Un établissement marqué CHU doit avoir type='CHU'.")

    def __str__(self):
        return f"{self.name} [{self.code}]"


class Department(UUIDModel, TimeStampedModel, TenantScopedModel):
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="departments")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, null=True, blank=True)  # +++
    type = models.CharField(max_length=40, default="GENERAL")

    class Meta:
        verbose_name = _("Service hospitalier")
        verbose_name_plural = _("Services hospitaliers")
        unique_together = (("facility", "name"),)
        indexes = [
            models.Index(fields=["tenant_key", "type"]),
            models.Index(fields=["facility", "code"]),
        ]


class Practitioner(UUIDModel, TimeStampedModel, TenantScopedModel):
    # lier a l,User
    matricule = models.CharField(max_length=64, db_index=True)
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="practitioners")
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    role = models.CharField(max_length=40)
    specialty = models.CharField(max_length=120, null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Professionnel de santé")
        verbose_name_plural = _("Professionnels de santé")
        unique_together = (("facility", "matricule"),)  # +++
        indexes = [
            models.Index(fields=["tenant_key", "matricule"]),
            models.Index(fields=["active"]),
        ]


class Bed(UUIDModel, TimeStampedModel, TenantScopedModel):
    # Chambres
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="beds")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="beds")
    code = models.CharField(max_length=32)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Lit")
        verbose_name_plural = _("Lits")
        unique_together = (("facility", "code"),)
        indexes = [
            models.Index(fields=["tenant_key", "active"]),
            models.Index(fields=["department"]),
        ]


class Patient(UUIDModel, TimeStampedModel):
    """
    Identité pseudonymisée (MPI), option filiation directe (father/mother)
    et statut vital.
    """
    # Identité pseudonymisée
    mpi = models.CharField(max_length=128, unique=True, db_index=True)
#CMU
    # (Optionnel) Nom(s) non sensibles / initiales si besoin (éviter le PII clair)
    given_name = models.CharField(max_length=120, null=True, blank=True)
    family_name = models.CharField(max_length=120, null=True, blank=True)

    birth_date = models.DateField(null=True, blank=True)
    sex = models.CharField(
        max_length=1,
        choices=[("M", "Male"), ("F", "Female"), ("O", "Other")],
        null=True, blank=True
    )

    # Contact minimal (hashés si sensibles)
    phone_hash = models.CharField(max_length=128, null=True, blank=True)
    national_id_hash = models.CharField(max_length=128, null=True, blank=True)

    # Dernière commune de résidence connue (accélère les requêtes courantes)
    residence_commune = models.ForeignKey(
        Commune, null=True, blank=True, on_delete=models.SET_NULL, related_name="patients_current"
    )

    # Filiation directe (facultatif) : liens rapides
    father = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children_as_father"
    )
    mother = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children_as_mother"
    )

    # Statut vital
    is_deceased = models.BooleanField(default=False, db_index=True)
    death_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = _("Patient")
        verbose_name_plural = _("Patients")
        indexes = [
            models.Index(fields=["family_name", "given_name"]),
            models.Index(fields=["birth_date"]),
            models.Index(fields=["is_deceased", "death_date"]),
        ]

    def clean(self):
        if self.is_deceased and not self.death_date:
            raise ValidationError("death_date is required when is_deceased=True.")

    # Siblings (frères/soeurs) inférés via parents si disponibles
    @property
    def siblings_via_parents(self):
        sibs = Patient.objects.none()
        if self.father_id:
            sibs = sibs.union(
                Patient.objects.filter(father_id=self.father_id).exclude(id=self.id)
            )
        if self.mother_id:
            sibs = sibs.union(
                Patient.objects.filter(mother_id=self.mother_id).exclude(id=self.id)
            )
        return sibs.distinct()

    def __str__(self):
        label = self.mpi
        if self.family_name or self.given_name:
            label = f"{self.family_name or ''} {self.given_name or ''} ({self.mpi})".strip()
        return label


class PatientResidence(UUIDModel, TimeStampedModel):
    """
    Historique des résidences du patient :
    - commune : rattachement géographique
    - address_text : précision libre si besoin (éviter PII sensible)
    - period: from_date -> to_date (to_date null = courant)
    - is_primary: une seule résidence principale active à la fois
    """
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="residences")
    commune = models.ForeignKey(Commune, on_delete=models.PROTECT, related_name="residents")
    address_text = models.CharField(max_length=255, null=True, blank=True)

    from_date = models.DateField(db_index=True)
    to_date = models.DateField(null=True, blank=True, db_index=True)

    is_primary = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = _("Résidence du patient")
        verbose_name_plural = _("Résidences du patient")
        indexes = [
            models.Index(fields=["patient", "from_date"]),
            models.Index(fields=["patient", "to_date"]),
            models.Index(fields=["patient", "is_primary"]),
            models.Index(fields=["commune"]),
        ]
        # Un seul enregistrement "primaire" actif par patient
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=models.Q(is_primary=True, to_date__isnull=True),
                name="uniq_current_primary_residence_per_patient",
            )
        ]

    def clean(self):
        # bornes logiques
        if self.to_date and self.to_date < self.from_date:
            raise ValidationError("to_date must be >= from_date.")

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)

        # Si cette résidence est active et primaire, mettre à jour le "cache" sur Patient
        if self.is_primary and self.to_date is None:
            Patient.objects.filter(id=self.patient_id).update(residence_commune_id=self.commune_id)

        # Si on crée une nouvelle résidence primaire active, on peut clore l’ancienne automatiquement (optionnel)
        if creating and self.is_primary and self.to_date is None:
            PatientResidence.objects.filter(
                patient_id=self.patient_id, is_primary=True, to_date__isnull=True
            ).exclude(id=self.id).update(to_date=timezone.now().date())


# =========================
#       LIENS FAMILIAUX
# =========================
class Kinship(UUIDModel, TimeStampedModel):
    """
    Lien familial générique entre deux patients.
    On impose une direction canonique :
      - PARENT_OF  : A -> B (A est parent de B)
      - CHILD_OF   : A -> B (A est enfant de B)
      - SIBLING_OF : A -> B (fratrie, lien symétrique)
      - SPOUSE_OF  : A -> B (conjoint, symétrique)
      - GUARDIAN_OF: A -> B (tuteur -> pupille)
    Des helpers (create_pair, ensure_symmetry) gèrent la réciprocité quand nécessaire.
    """

    class Relation(models.TextChoices):
        PARENT_OF = "PARENT_OF", "Parent of"
        CHILD_OF = "CHILD_OF", "Child of"
        SIBLING_OF = "SIBLING_OF", "Sibling of"
        SPOUSE_OF = "SPOUSE_OF", "Spouse of"
        GUARDIAN_OF = "GUARDIAN_OF", "Guardian of"

    src = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="kinship_out")
    dst = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="kinship_in")
    relation = models.CharField(max_length=16, choices=Relation.choices)

    # Période de validité du lien (utile pour tuteur, conjoint, etc.)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = _("Lien familial")
        verbose_name_plural = _("Liens familiaux")
        indexes = [
            models.Index(fields=["src", "relation"]),
            models.Index(fields=["dst", "relation"]),
        ]
        unique_together = ("src", "dst", "relation")

    def clean(self):
        if self.src_id == self.dst_id:
            raise ValidationError("src and dst cannot be the same patient.")
        if self.valid_to and self.valid_from and self.valid_to < self.valid_from:
            raise ValidationError("valid_to must be >= valid_from.")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._ensure_symmetry()

    # --- Helpers de symétrie ---
    def _ensure_symmetry(self):
        """
        Crée/maintient le lien réciproque quand la relation est symétrique
        ou nécessite une contrepartie (SIBLING_OF, SPOUSE_OF, PARENT/CHILD).
        """
        inverse = None
        if self.relation == self.Relation.SIBLING_OF:
            inverse = self.Relation.SIBLING_OF
        elif self.relation == self.Relation.SPOUSE_OF:
            inverse = self.Relation.SPOUSE_OF
        elif self.relation == self.Relation.PARENT_OF:
            inverse = self.Relation.CHILD_OF
        elif self.relation == self.Relation.CHILD_OF:
            inverse = self.Relation.PARENT_OF

        if not inverse:
            return

        Kinship.objects.get_or_create(
            src=self.dst, dst=self.src, relation=inverse,
            defaults={"valid_from": self.valid_from, "valid_to": self.valid_to}
        )

    # --- Méthodes d'accès pratique ---
    @staticmethod
    def add_parent_child(parent: Patient, child: Patient, when=None):
        return Kinship.objects.get_or_create(
            src=parent, dst=child, relation=Kinship.Relation.PARENT_OF,
            defaults={"valid_from": when}
        )

    @staticmethod
    def add_siblings(a: Patient, b: Patient, when=None):
        Kinship.objects.get_or_create(
            src=a, dst=b, relation=Kinship.Relation.SIBLING_OF,
            defaults={"valid_from": when}
        )
        Kinship.objects.get_or_create(
            src=b, dst=a, relation=Kinship.Relation.SIBLING_OF,
            defaults={"valid_from": when}
        )

    @staticmethod
    def add_spouses(a: Patient, b: Patient, when=None):
        Kinship.objects.get_or_create(
            src=a, dst=b, relation=Kinship.Relation.SPOUSE_OF,
            defaults={"valid_from": when}
        )
        Kinship.objects.get_or_create(
            src=b, dst=a, relation=Kinship.Relation.SPOUSE_OF,
            defaults={"valid_from": when}
        )


class VisitType(UUIDModel, TimeStampedModel):
    """
    Référentiel des types de visite (ex: Urgences, Hospitalisation, Consultation).
    """
    code = models.CharField(max_length=16, unique=True, db_index=True)  # ER, IPD, OPD, ...
    label = models.CharField(max_length=128)  # Libellé affiché
    category = models.CharField(max_length=32, null=True, blank=True)  # Optionnel (ex: AMBULATORY/INPATIENT)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=100)  # Pour ordonner dans l’UI

    class Meta:
        verbose_name = _("Type de visite")
        verbose_name_plural = _("Types de visite")
        indexes = [
            models.Index(fields=["active", "sort_order"]),
        ]

    def __str__(self):
        return f"{self.label} [{self.code}]"


class Encounter(UUIDModel, TimeStampedModel, TenantScopedModel):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="encounters")
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="encounters")
    department = models.ForeignKey('Department', null=True, blank=True, on_delete=models.SET_NULL)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(null=True, blank=True)
    visit_type = models.ForeignKey('VisitType', on_delete=models.PROTECT,
                                   related_name='encounters')  # <<< CHANGEMENT

    outcome = models.CharField(max_length=64, null=True, blank=True)  # DISCHARGED, REFERRED, DECEASED...

    class Meta:
        verbose_name = _("Séjour / Visite")
        verbose_name_plural = _("Séjours / Visites")
        indexes = [
            models.Index(fields=["tenant_key", "start_at"]),
            models.Index(fields=["facility", "start_at"]),
            models.Index(fields=["patient"]),
        ]


class EncounterEvent(UUIDModel, TimeStampedModel, TenantScopedModel):
    """
    Trace tout le cycle de séjour: ADMIT / TRANSFER / DISCHARGE.
    Sert d'audit et pilote la gestion des lits.
    """

    class Kind(models.TextChoices):
        ADMIT = "ADMIT", _("Admission")
        TRANSFER = "TRANSFER", _("Transfert")
        DISCHARGE = "DISCHARGE", _("Sortie")

    encounter = models.ForeignKey('Encounter', on_delete=models.PROTECT, related_name="events")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    effective_at = models.DateTimeField(db_index=True)

    from_department = models.ForeignKey('Department', null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name="+")
    to_department = models.ForeignKey('Department', null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="+")
    bed = models.ForeignKey('Bed', null=True, blank=True, on_delete=models.SET_NULL)

    note = models.CharField(max_length=255, null=True, blank=True)

    def _derive_tenant_key(self):
        # Récupère via encounter -> facility
        if self.encounter_id and self.encounter and self.encounter.facility_id:
            self.tenant_key = self.encounter.facility.root().code

    class Meta:
        verbose_name = _("Événement de séjour")
        verbose_name_plural = _("Événements de séjour")
        indexes = [
            models.Index(fields=["tenant_key", "effective_at"]),
            models.Index(fields=["encounter", "kind"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(kind="ADMIT") | models.Q(to_department__isnull=False),
                name="admit_needs_to_department",
            ),
            models.CheckConstraint(
                check=~models.Q(kind="TRANSFER") | (
                        models.Q(from_department__isnull=False) & models.Q(to_department__isnull=False)),
                name="transfer_needs_from_and_to",
            ),
        ]


class BedOccupancy(UUIDModel, TimeStampedModel, TenantScopedModel):
    bed = models.ForeignKey('Bed', on_delete=models.PROTECT)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    from_ts = models.DateTimeField(db_index=True)
    to_ts = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=16, default="OCCUPIED")

    def _derive_tenant_key(self):
        if self.bed_id and self.bed and self.bed.facility_id:
            root = self.bed.facility.root() if hasattr(self.bed.facility, "root") else self.bed.facility
            self.tenant_key = root.code

    class Meta:
        verbose_name = _("Occupation de lit")
        verbose_name_plural = _("Occupations de lit")
        indexes = [
            models.Index(fields=["tenant_key", "from_ts"]),
            models.Index(fields=["bed"]),
            models.Index(fields=["patient"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(to_ts__isnull=True) | models.Q(to_ts__gte=models.F("from_ts")),
                name="bedocc_time_order_ok",
            ),
            # Une seule occupation ouverte par lit
            models.UniqueConstraint(
                fields=["bed"],
                condition=models.Q(to_ts__isnull=True),
                name="uniq_open_bed_occupancy",
            ),
        ]


class ClinicalOrder(UUIDModel, TimeStampedModel, TenantScopedModel):
    """
    Ordre clinique générique (LAB / IMAGING / MED / PROC).
    Regroupe les lignes (OrderItem). Porteur du statut global.
    """

    class Category(models.TextChoices):
        LAB = "LAB", _("Laboratoire")
        IMAGING = "IMAGING", _("Imagerie")
        MED = "MED", _("Médicament")
        PROC = "PROC", _("Procédure/Acte")

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Brouillon")
        PLACED = "PLACED", _("Prescrite")
        IN_PROGRESS = "IN_PROGRESS", _("En cours")
        COMPLETED = "COMPLETED", _("Terminée")
        CANCELLED = "CANCELLED", _("Annulée")

    encounter = models.ForeignKey('Encounter', on_delete=models.PROTECT, related_name="orders")
    category = models.CharField(max_length=16, choices=Category.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLACED, db_index=True)
    ordered_by = models.ForeignKey('Practitioner', null=True, blank=True, on_delete=models.SET_NULL)
    reason = models.CharField(max_length=255, null=True, blank=True)

    def _derive_tenant_key(self):
        if self.encounter_id and self.encounter and self.encounter.facility_id:
            self.tenant_key = self.encounter.facility.root().code

    class Meta:
        verbose_name = _("Commande clinique")
        verbose_name_plural = _("Commandes cliniques")
        indexes = [
            models.Index(fields=["tenant_key", "category", "status"]),
            models.Index(fields=["encounter"]),
        ]


class OrderItem(UUIDModel, TimeStampedModel, TenantScopedModel):
    """
    Ligne d'une commande: un test labo, un examen imagerie, un acte, un médicament.
    Les codifications pointent vers ICD/LOINC/Act/Medication selon le cas.
    """
    order = models.ForeignKey(ClinicalOrder, on_delete=models.CASCADE, related_name="items")
    code = models.CharField(max_length=64, db_index=True)  # LOINC (LAB), code radiologie, code acte, code médicament
    label = models.CharField(max_length=255)
    status = models.CharField(max_length=16, default="ORDERED")  # ORDERED / IN_PROGRESS / DONE / CANCELLED
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def _derive_tenant_key(self):
        if self.order_id and self.order and self.order.encounter_id:
            self.tenant_key = self.order.encounter.facility.root().code

    class Meta:
        verbose_name = _("Ligne de commande")
        verbose_name_plural = _("Lignes de commande")
        indexes = [
            models.Index(fields=["tenant_key", "status"]),
            models.Index(fields=["code"]),
        ]


# 2) Procedure : via encounter -> facility
class Procedure(UUIDModel, TimeStampedModel, TenantScopedModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.PROTECT, related_name="procedures")
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    performed_at = models.DateTimeField(db_index=True)
    performer = models.ForeignKey('Practitioner', null=True, blank=True, on_delete=models.SET_NULL)

    def _derive_tenant_key(self):
        if self.encounter_id and self.encounter and self.encounter.facility_id:
            self.tenant_key = self.encounter.facility.root().code

    class Meta:
        verbose_name = _("Acte / Procédure")
        verbose_name_plural = _("Actes / Procédures")
        indexes = [
            models.Index(fields=["tenant_key", "performed_at"]),
            models.Index(fields=["encounter"]),
            models.Index(fields=["code"]),
        ]


# 3) DiagnosticReport : via encounter -> facility
class DiagnosticReport(UUIDModel, TimeStampedModel, TenantScopedModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.PROTECT, related_name="reports")
    modality = models.CharField(max_length=24, default="LAB")  # LAB, IMG...
    status = models.CharField(max_length=24, default="FINAL")
    issued_at = models.DateTimeField(db_index=True)

    def _derive_tenant_key(self):
        if self.encounter_id and self.encounter and self.encounter.facility_id:
            self.tenant_key = self.encounter.facility.root().code

    class Meta:
        verbose_name = _("Compte rendu diagnostique")
        verbose_name_plural = _("Comptes rendus diagnostiques")
        indexes = [
            models.Index(fields=["tenant_key", "issued_at"]),
            models.Index(fields=["encounter"]),
            models.Index(fields=["modality", "status"]),
        ]


class Specimen(UUIDModel, TimeStampedModel, TenantScopedModel):
    """
    Échantillon biologique associé à une ou plusieurs lignes LAB.
    """

    class Type(models.TextChoices):
        BLOOD = "BLOOD", _("Sang")
        URINE = "URINE", _("Urine")
        STOOL = "STOOL", _("Selles")
        SWAB = "SWAB", _("Écouvillon")
        OTHER = "OTHER", _("Autre")

    encounter = models.ForeignKey('Encounter', on_delete=models.PROTECT)
    collected_at = models.DateTimeField(db_index=True)
    specimen_type = models.CharField(max_length=16, choices=Type.choices, default=Type.BLOOD)
    collector = models.ForeignKey('Practitioner', null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.CharField(max_length=255, null=True, blank=True)

    items = models.ManyToManyField(OrderItem, related_name="specimens", blank=True)

    def _derive_tenant_key(self):
        if self.encounter_id and self.encounter and self.encounter.facility_id:
            self.tenant_key = self.encounter.facility.root().code

    class Meta:
        verbose_name = _("Échantillon biologique")
        verbose_name_plural = _("Échantillons biologiques")
        indexes = [models.Index(fields=["tenant_key", "collected_at"])]


# 4) Observation : via encounter -> facility
class Observation(UUIDModel, TimeStampedModel, TenantScopedModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.PROTECT, related_name="observations")
    report = models.ForeignKey(DiagnosticReport, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="observations")
    loinc_code = models.CharField(max_length=32, db_index=True)
    value = models.CharField(max_length=256, null=True, blank=True)
    unit = models.CharField(max_length=32, null=True, blank=True)
    result_flag = models.CharField(max_length=16, null=True, blank=True)
    observed_at = models.DateTimeField(db_index=True)

    def _derive_tenant_key(self):
        if self.encounter_id and self.encounter and self.encounter.facility_id:
            self.tenant_key = self.encounter.facility.root().code

    class Meta:
        verbose_name = _("Observation / Résultat")
        verbose_name_plural = _("Observations / Résultats")
        indexes = [
            models.Index(fields=["tenant_key", "observed_at", "loinc_code"]),
            models.Index(fields=["encounter"]),
        ]


class Payer(UUIDModel, TimeStampedModel):
    code = models.CharField(max_length=32, unique=True, db_index=True)  # mutuelle, assurance, privé
    label = models.CharField(max_length=160)

    class Meta:
        verbose_name = _("Payeur / Assurance")
        verbose_name_plural = _("Payeurs / Assurances")


# 5) Invoice : via encounter -> facility
class Invoice(UUIDModel, TimeStampedModel, TenantScopedModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.PROTECT, related_name="invoices")
    payer = models.ForeignKey(Payer, null=True, blank=True, on_delete=models.SET_NULL)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=16, default="DRAFT")
    issued_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def _derive_tenant_key(self):
        if self.encounter_id and self.encounter and self.encounter.facility_id:
            self.tenant_key = self.encounter.facility.root().code

    class Meta:
        verbose_name = _("Facture")
        verbose_name_plural = _("Factures")
        indexes = [
            models.Index(fields=["tenant_key", "issued_at", "status"]),
            models.Index(fields=["encounter"]),
        ]


class InvoiceLine(UUIDModel, TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    act_code = models.CharField(max_length=32)
    label = models.CharField(max_length=255)
    qty = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = _("Ligne de facture")
        verbose_name_plural = _("Lignes de facture")
        constraints = [
            models.CheckConstraint(check=models.Q(qty__gt=0), name="invoiceline_qty_gt_0"),
            models.CheckConstraint(check=models.Q(unit_price__gte=0), name="invoiceline_unit_price_ge_0"),
        ]

    @property
    def amount(self):
        return self.qty * self.unit_price


class Appointment(UUIDModel, TimeStampedModel, TenantScopedModel):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    practitioner = models.ForeignKey(Practitioner, null=True, blank=True, on_delete=models.SET_NULL)
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=16, default="SCHEDULED")  # SCHEDULED, DONE, MISSED, CANCELLED
    reason = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = _("Rendez-vous")
        indexes = [
            models.Index(fields=["tenant_key", "start_at"]),
            models.Index(fields=["practitioner", "start_at"]),
            models.Index(fields=["patient", "start_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_at__gt=models.F("start_at")),
                name="appt_time_valid",
            ),
            # Un RDV actif identique exact (praticien+start) interdit
            models.UniqueConstraint(
                fields=["practitioner", "start_at"],
                name="uniq_practitioner_start",
            ),
        ]


# 6) Referral : choisir la clé de périmètre (source ou cible)
class Referral(UUIDModel, TimeStampedModel, TenantScopedModel):
    from_facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="referrals_out")
    to_facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="referrals_in")
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    encounter_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(max_length=16, default="OPEN")  # OPEN, ACCEPTED, REJECTED, CLOSED

    def _derive_tenant_key(self):
        # Politique : on "scope" sur la source (from_facility)
        root = self.from_facility.root() if self.from_facility_id else None
        if root:
            self.tenant_key = root.code

    class Meta:
        verbose_name = _("Référence / Transfert")
        verbose_name_plural = _("Références / Transferts")
        indexes = [
            models.Index(fields=["tenant_key", "status"]),
            models.Index(fields=["from_facility"]),
            models.Index(fields=["to_facility"]),
            models.Index(fields=["patient"]),
        ]


class CodeAct(UUIDModel, TimeStampedModel):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    label = models.CharField(max_length=255)
    category = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        verbose_name = _("Code d'acte")
        verbose_name_plural = _("Codes d'actes")


class CodeDiagICD10(UUIDModel, TimeStampedModel):
    icd10 = models.CharField(max_length=8, unique=True, db_index=True)
    label = models.CharField(max_length=255)

    class Meta:
        verbose_name = _("Code CIM-10")
        verbose_name_plural = _("Codes CIM-10")


class CodeLabLOINC(UUIDModel, TimeStampedModel):
    loinc = models.CharField(max_length=16, unique=True, db_index=True)
    label = models.CharField(max_length=255)

    class Meta:
        verbose_name = _("Code LOINC (laboratoire)")
        verbose_name_plural = _("Codes LOINC (laboratoire)")


class ImagingStudy(UUIDModel, TimeStampedModel, TenantScopedModel):
    """
    Étude d'imagerie réalisée. Référence DICOM/PACS.
    """
    order_item = models.OneToOneField(OrderItem, on_delete=models.PROTECT, related_name="imaging_study")
    modality = models.CharField(max_length=16, default="XR")  # XR/CT/MR/US/...
    accession_number = models.CharField(max_length=64, db_index=True, null=True, blank=True)
    study_instance_uid = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    performed_at = models.DateTimeField(db_index=True, null=True, blank=True)
    images_count = models.IntegerField(default=0)

    def _derive_tenant_key(self):
        if self.order_item_id and self.order_item and self.order_item.order_id:
            self.tenant_key = self.order_item.order.encounter.facility.root().code

    class Meta:
        verbose_name = _("Étude d’imagerie")
        verbose_name_plural = _("Études d’imagerie")
        indexes = [
            models.Index(fields=["tenant_key", "performed_at"]),
            models.Index(fields=["accession_number"]),
            models.Index(fields=["study_instance_uid"]),
        ]


class Medication(UUIDModel, TimeStampedModel):
    """
    Référentiel médicaments (CIP/ATC/code interne).
    """
    code = models.CharField(max_length=64, unique=True, db_index=True)
    label = models.CharField(max_length=255)
    form = models.CharField(max_length=64, null=True, blank=True)  # Comprimé, sirop...
    strength = models.CharField(max_length=64, null=True, blank=True)  # 500 mg, 1g/5ml...

    class Meta:
        verbose_name = _("Médicament")
        verbose_name_plural = _("Médicaments")
        indexes = [models.Index(fields=["label"])]


class Prescription(UUIDModel, TimeStampedModel, TenantScopedModel):
    """
    Prescription médicamenteuse (ordonnance) : lignes + statut.
    """
    encounter = models.ForeignKey('Encounter', on_delete=models.PROTECT, related_name="prescriptions")
    prescriber = models.ForeignKey('Practitioner', null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, default="ACTIVE")  # ACTIVE/PAUSED/STOPPED/COMPLETED/CANCELLED
    note = models.CharField(max_length=255, null=True, blank=True)

    def _derive_tenant_key(self):
        if self.encounter_id and self.encounter and self.encounter.facility_id:
            self.tenant_key = self.encounter.facility.root().code

    class Meta:
        verbose_name = _("Prescription")
        verbose_name_plural = _("Prescriptions")
        indexes = [models.Index(fields=["tenant_key", "status"])]


class PrescriptionLine(UUIDModel, TimeStampedModel, TenantScopedModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="lines")
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT)
    dose = models.CharField(max_length=64)  # ex: 500 mg
    route = models.CharField(max_length=32)  # PO/IV/IM/SC…
    frequency = models.CharField(max_length=64)  # ex: 1 cp x3/j
    duration_days = models.IntegerField(default=1)
    prn = models.BooleanField(default=False)  # si besoin
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    def _derive_tenant_key(self):
        if self.prescription_id:
            self.tenant_key = self.prescription.tenant_key

    class Meta:
        verbose_name = _("Ligne de prescription")
        verbose_name_plural = _("Lignes de prescription")
        indexes = [models.Index(fields=["tenant_key", "start_at"])]


class MedicationDispense(UUIDModel, TimeStampedModel, TenantScopedModel):
    """
    Dispense par la pharmacie (remise au patient/au service).
    """
    prescription_line = models.ForeignKey(PrescriptionLine, on_delete=models.PROTECT, related_name="dispenses")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    dispensed_at = models.DateTimeField(db_index=True)
    dispenser = models.ForeignKey('Practitioner', null=True, blank=True, on_delete=models.SET_NULL)

    def _derive_tenant_key(self):
        if self.prescription_line_id:
            self.tenant_key = self.prescription_line.tenant_key

    class Meta:
        verbose_name = _("Dispensation")
        verbose_name_plural = _("Dispensations")
        indexes = [models.Index(fields=["tenant_key", "dispensed_at"])]


class MedicationAdministration(UUIDModel, TimeStampedModel, TenantScopedModel):
    """
    Administration réelle (MAR infirmier·e).
    """
    prescription_line = models.ForeignKey(PrescriptionLine, on_delete=models.PROTECT, related_name="administrations")
    administered_at = models.DateTimeField(db_index=True)
    dose_given = models.CharField(max_length=64)
    nurse = models.ForeignKey('Practitioner', null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=255, null=True, blank=True)

    def _derive_tenant_key(self):
        if self.prescription_line_id:
            self.tenant_key = self.prescription_line.tenant_key

    class Meta:
        verbose_name = _("Administration médicamenteuse")
        verbose_name_plural = _("Administrations médicamenteuses")
        indexes = [models.Index(fields=["tenant_key", "administered_at"])]


class DischargeSummary(UUIDModel, TimeStampedModel, TenantScopedModel):
    encounter = models.OneToOneField('Encounter', on_delete=models.PROTECT, related_name="discharge_summary")
    outcome = models.CharField(max_length=32)  # DISCHARGED_HOME / REFERRED / DECEASED / LAMA / ...
    primary_icd10 = models.ForeignKey('CodeDiagICD10', null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(null=True, blank=True)
    discharged_at = models.DateTimeField(db_index=True)

    def _derive_tenant_key(self):
        if self.encounter_id and self.encounter and self.encounter.facility_id:
            self.tenant_key = self.encounter.facility.root().code

    class Meta:
        verbose_name = _("Résumé de sortie")
        verbose_name_plural = _("Résumés de sortie")
        indexes = [models.Index(fields=["tenant_key", "discharged_at"])]
