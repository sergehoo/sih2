from django.db import connection
from django.utils.deprecation import MiddlewareMixin


def _roles(token: dict) -> set:
    roles = set()
    if not token:
        return roles
    roles |= set(token.get("realm_access", {}).get("roles", []))
    for v in token.get("resource_access", {}).values():
        roles |= set(v.get("roles", []))
    return roles


class PostgresScopeMiddleware(MiddlewareMixin):
    """
    Lit le JWT (déjà décodé) dans request.auth (ex: via DRF SimpleJWT ou un auth middleware)
    et positionne les variables de session Postgres utilisées par les policies RLS :
      - app.tenant_key  : pour le personnel (scopé facility/CHU)
      - app.patient_mpi : pour les patients (accès à leur propre dossier)
    Convention de claims JWT attendues :
      - "tenant_key"   (ex: "CHU-COCODY")
      - "patient_mpi"  (ex: "mpi_xxx")
      - rôles : "ROLE_PATIENT", "ROLE_MEDECIN", "ROLE_ADMIN_CHU", etc.
    """

    def process_request(self, request):
        token = getattr(request, "auth", None) or {}
        roles = _roles(token)
        tenant_key = token.get("tenant_key")
        patient_mpi = token.get("patient_mpi")

        with connection.cursor() as cur:
            # Réinitialise proprement
            cur.execute("SELECT set_config('app.tenant_key', '', true);")
            cur.execute("SELECT set_config('app.patient_mpi', '', true);")

            if "ROLE_PATIENT" in roles and patient_mpi:
                # Mode patient : accès restreint à ses données
                cur.execute("SELECT set_config('app.patient_mpi', %s, true);", [patient_mpi])
                return

            # Mode personnel : scope par tenant_key (facility racine)
            if tenant_key:
                cur.execute("SELECT set_config('app.tenant_key', %s, true);", [tenant_key])
