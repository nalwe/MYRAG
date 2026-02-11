from django.db import transaction
from django.core.exceptions import PermissionDenied

from accounts.models import Organization


class QuotaExceeded(Exception):
    pass


@transaction.atomic
def consume_tokens(*, organization: Organization, tokens: int):
    """
    Deduct tokens safely from organization quota.
    """

    if not organization:
        # Global / superuser usage (no quota)
        return

    # Lock row to prevent race condition
    org = Organization.objects.select_for_update().get(id=organization.id)

    if org.api_tokens_used + tokens > org.api_token_limit:
        raise QuotaExceeded(
            f"API quota exceeded for {org.name}. "
            f"Limit={org.api_token_limit}, Used={org.api_tokens_used}"
        )

    org.api_tokens_used += tokens
    org.save(update_fields=["api_tokens_used"])
