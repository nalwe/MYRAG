# accounts/utils.py

from django.contrib.auth.models import AnonymousUser, Permission
from accounts.models import OrganizationMember, Profile


# =====================================================
# 🔄 PERMISSION SYNC ENGINE (ACCOUNT TIER ONLY)
# =====================================================
# IMPORTANT:
# - Profile.role = pricing tier (basic / premium)
# - Org authority is handled by OrganizationMember
# - Superusers bypass everything
# =====================================================

ROLE_PERMISSIONS = {
    Profile.ROLE_BASIC: [
        "documents.view_document",
    ],
    Profile.ROLE_PREMIUM: [
        "documents.view_document",
        "documents.add_document",
    ],
}


def sync_user_permissions(user):
    """
    Sync Django permissions based on Profile.role (pricing tier).
    Org admin powers are enforced at the view level.
    """
    if not user or not user.is_authenticated:
        return

    # Superuser gets everything
    if user.is_superuser:
        return

    # Remove all custom permissions
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
            pass


# =====================================================
# 👤 USER ROLE HELPERS
# =====================================================

def get_user_role(user):
    """
    Returns: 'basic', 'premium', or None
    """
    if not user or isinstance(user, AnonymousUser):
        return None

    return getattr(user.profile, "role", None)


# =====================================================
# 🏢 ORGANIZATION HELPERS
# =====================================================

def get_user_organization(user):
    """
    Returns user's active organization or None
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
    Returns active OrganizationMember or None
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


# =====================================================
# 🔐 ORG ADMIN & PERMISSION CHECKS (AUTHORITATIVE)
# =====================================================

def is_org_admin(user):
    """
    TRUE source of org admin authority.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return OrganizationMember.objects.filter(
        user=user,
        role="admin",
        is_active=True,
        organization__is_active=True,
    ).exists()


def can_manage_documents(user):
    """
    Premium users AND org admins can manage documents.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if getattr(user.profile, "role", None) == Profile.ROLE_PREMIUM:
        return True

    return is_org_admin(user)


def can_manage_org_users(user):
    """
    Only org admins can manage users in their org.
    """
    return is_org_admin(user)


# =====================================================
# 🚦 ORGANIZATION LIMITS
# =====================================================

def can_add_user_to_org(organization):
    """
    Enforce organization user limits.
    """
    if not organization or not organization.is_active:
        return False

    return organization.user_count < organization.max_users
