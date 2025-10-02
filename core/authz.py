# core/authz.py
from rest_framework.permissions import BasePermission

class HasKCRealmRole(BasePermission):
    """
    Ex: @permission_classes([HasKCRealmRole])
    et dans la vue: required_roles = {"admin", "manager"}
    """
    def has_permission(self, request, view):
        required = getattr(view, "required_roles", set())
        if not required:
            return True
        token = getattr(request, "auth", None)
        if not token:
            return False
        roles = set(token.payload.get("realm_access", {}).get("roles", []))
        # Ou: roles = set(token.payload.get("resource_access", {}).get("sih-api", {}).get("roles", []))
        return bool(required & roles)