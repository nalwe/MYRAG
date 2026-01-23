# accounts/utils.py
from accounts.models import OrganizationMember



def get_user_role(user):
    """
    Return one of: 'admin', 'premium', 'basic', or None if not authenticated.
    Adapt to how your app stores roles (profile, is_staff, etc.).
    """
    if not user or not user.is_authenticated:
        return None
    if user.is_staff:
        return "admin"
    role = getattr(user, "profile", None)
    if role and hasattr(role, "role"):
        return getattr(role, "role")
    # Fallback: if you store a direct flag
    if getattr(user, "is_premium", False):
        return "premium"
    return "basic"  # default fallback


def get_user_organization(user):
    return OrganizationMember.objects.filter(user=user).first()


def is_org_admin(user):
    return OrganizationMember.objects.filter(
        user=user,
        role="admin"
    ).exists()


MAX_ORG_ADMINS = 5

def can_add_admin(organization):
    return (
        OrganizationMember.objects.filter(
            organization=organization,
            role="admin"
        ).count() < MAX_ORG_ADMINS
    )




def get_active_org_member(user):
    """
    Returns the active OrganizationMember for a user or None.
    Safely handles users without organization membership.
    """

    if not user or not user.is_authenticated:
        return None

    return (
        OrganizationMember.objects
        .select_related("organization")
        .filter(
            user=user,
            organization__is_active=True,
        )
        .first()
    )

