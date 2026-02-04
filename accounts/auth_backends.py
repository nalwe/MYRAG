from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied


class OrganizationActiveBackend(ModelBackend):
    """
    Prevent login if user's organization is archived.
    """

    def user_can_authenticate(self, user):
        # First run default Django checks
        can_auth = super().user_can_authenticate(user)
        if not can_auth:
            return False

        try:
            profile = user.profile
            organization = getattr(profile, "organization", None)

            # ❌ Block if organization is archived
            if organization and not organization.is_active:
                return False

        except Exception:
            # Fail-safe: if profile missing, allow (or change to False if you prefer)
            pass

        return True
