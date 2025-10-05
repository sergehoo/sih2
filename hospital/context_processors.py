# sigh/hospital/context_processors.py
from django.core.exceptions import ObjectDoesNotExist
from typing import Any, Dict


def user_profile(request) -> Dict[str, Any]:
    """
    Injecte dans tous les templates :
      - profile  : request.user.userprofile (ou None)
      - facility : profile.facility
      - roles    : liste des rôles ex. ["ROLE_MEDECIN", ...]
      - depts    : liste des départements ex. ["cardiologie", "labo"]
      - scope    : niveau (SERVICE/DISTRICT/REGION/POLE/NATIONAL)
    """
    profile = None
    user = getattr(request, "user", None)

    if getattr(user, "is_authenticated", False):
        try:
            profile = user.userprofile  # OneToOne reverse
        except (ObjectDoesNotExist, AttributeError):
            profile = None

    facility = getattr(profile, "facility", None)
    roles = getattr(profile, "roles", None) or []
    depts = getattr(profile, "departments", None) or []
    scope = getattr(profile, "scope_level", None)

    return {
        "profile": profile,
        "facility": facility,
        "roles": roles,
        "depts": depts,
        "scope": scope,
    }
