# accounts/utils.py

from django.contrib.auth.models import AnonymousUser
from accounts.models import OrganizationMember, Profile


from django.contrib.auth.models import Permission


# ============================
# 🔄 PERMISSION SYNC ENGINE
# ============================

ROLE_PERMISSIONS = {
    "basic": [
        "documents.view_document",
    ],
    "premium": [
        "documents.view_document",
        "documents.add_document",
    ],
    "org_admin": [
        "documents.view_document",
        "documents.add_document",
        "documents.delete_document",

        "accounts.view_user",
        "accounts.add_user",
        "accounts.change_user",
        "accounts.manage_organisation",
    ],
}


def sync_user_permissions(user):
    """
    Sync Django permissions based on Profile.role.
    This is the SINGLE source of truth for access control.
    """
    if not user or not user.is_authenticated:
        return

    # Superuser gets everything automatically
    if user.is_superuser:
        return

    # Clear existing permissions
    user.user_permissions.clear()

    if not hasattr(user, "profile"):
        return

    profile = user.profile

    if not profile.is_active or profile.is_suspended:
        return

    perms = ROLE_PERMISSIONS.get(profile.role, [])

    for perm in perms:
        app_label, codename = perm.split(".")
        try:
            permission = Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            )
            user.user_permissions.add(permission)
        except Permission.DoesNotExist:
            # Permission may not exist yet (safe to ignore)
            pass



# ============================
# 👤 USER ROLE HELPERS
# ============================

def get_user_role(user):
    """
    Returns one of: 'org_admin', 'premium', 'basic', or None.
    Superuser is handled by Django separately.
    """
    if not user or isinstance(user, AnonymousUser):
        return None

    if not hasattr(user, "profile"):
        return None

    return user.profile.role


# ============================
# 🏢 ORGANIZATION HELPERS
# ============================

def get_user_organization(user):
    """
    Returns the user's active organization or None.
    """
    if not user or not user.is_authenticated:
        return None

    profile = getattr(user, "profile", None)
    if not profile or not profile.organization:
        return None

    if not profile.organization.is_active:
        return None

    return profile.organization


def get_active_org_member(user):
    """
    Returns the active OrganizationMember for a user or None.
    Membership is informational, not authoritative.
    """
    if not user or not user.is_authenticated:
        return None

    return (
        OrganizationMember.objects
        .select_related("organization")
        .filter(
            user=user,
            organization__is_active=True,
            is_active=True,
        )
        .first()
    )


# ============================
# 🔐 ORG ADMIN CHECK (UI ONLY)
# ============================

def is_org_admin(user):
    """
    UI helper only.
    Real access control MUST use Django permissions.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if not hasattr(user, "profile"):
        return False

    return (
        user.profile.role == Profile.ROLE_ORG_ADMIN
        and user.profile.is_active
        and not user.profile.is_suspended()
    )


# ============================
# 🚦 ORG USER LIMIT HELPERS
# ============================

def can_add_user_to_org(organization):
    """
    Enforce organization user limits.
    """
    if not organization or not organization.is_active:
        return False

    return organization.user_count < organization.max_users
