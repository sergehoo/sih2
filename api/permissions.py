from rest_framework.permissions import BasePermission, SAFE_METHODS


def _roles(request):
    tok = getattr(request, "auth", None) or {}
    roles = set(tok.get("realm_access", {}).get("roles", []))
    for v in tok.get("resource_access", {}).values():
        roles |= set(v.get("roles", []))
    # On supporte aussi un header override pour dev/local si besoin
    hdr = request.META.get("HTTP_X_ROLES")
    if hdr:
        roles |= set([r.strip() for r in hdr.split(",") if r.strip()])
    return roles


class IsStaff(BasePermission):
    """ Personnel hospitalier (médecin, infirmier, admin CHU…). """
    STAFF_ROLES = {
        "ROLE_MEDECIN", "ROLE_INFIRMIER", "ROLE_ADMIN_CHU", "ROLE_SECRETAIRE",
        "ROLE_LAB", "ROLE_PHARMACY", "ROLE_FINANCE"
    }

    def has_permission(self, request, view):
        return len(_roles(request) & self.STAFF_ROLES) > 0


class IsPatient(BasePermission):
    def has_permission(self, request, view):
        return "ROLE_PATIENT" in _roles(request)


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class StaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return IsStaff().has_permission(request, view)


class IsSelfPatient(BasePermission):
    """ Vérifie qu’un patient authentifié a bien un patient_mpi dans le token. """

    def has_permission(self, request, view):
        tok = getattr(request, "auth", None) or {}
        return ("ROLE_PATIENT" in _roles(request)) and bool(tok.get("patient_mpi"))
