from django.contrib.auth.models import AnonymousUser


def is_authenticated(user):
    return user and not isinstance(user, AnonymousUser)


def is_org_admin(user):
    """
    Organisation admin or Django superuser.
    """
    if not is_authenticated(user):
        return False

    if user.is_superuser:
        return True

    return (
        hasattr(user, "profile")
        and user.profile.role == "org_admin"
        and user.profile.is_active
        and not user.profile.is_suspended()
    )


def is_premium(user):
    """
    Premium users only (superuser always allowed).
    """
    if not is_authenticated(user):
        return False

    if user.is_superuser:
        return True

    return (
        hasattr(user, "profile")
        and user.profile.role == "premium"
        and user.profile.is_active
        and not user.profile.is_suspended()
    )


def is_basic(user):
    """
    Any active user (basic, premium, org_admin).
    """
    if not is_authenticated(user):
        return False

    if user.is_superuser:
        return True

    return (
        hasattr(user, "profile")
        and user.profile.role in {"basic", "premium", "org_admin"}
        and user.profile.is_active
        and not user.profile.is_suspended()
    )
