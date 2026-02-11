from accounts.models import Profile
from accounts.utils import (
    is_org_admin,
    can_manage_documents,
    can_manage_org_users,
    get_user_organization,
)


def user_profile(request):
    """
    Expose the authenticated user's profile to templates.
    Read-only. Never create DB objects here.
    """
    if request.user.is_authenticated:
        try:
            return {
                "profile": request.user.profile,
                "organization": get_user_organization(request.user),
            }
        except Profile.DoesNotExist:
            return {
                "profile": None,
                "organization": None,
            }

    return {
        "profile": None,
        "organization": None,
    }


def permissions_context(request):
    """
    Centralized permission flags for templates.
    Templates should NEVER query models directly.
    """
    user = request.user

    return {
        "is_org_admin": is_org_admin(user),
        "can_manage_documents": can_manage_documents(user),
        "can_manage_org_users": can_manage_org_users(user),
    }
