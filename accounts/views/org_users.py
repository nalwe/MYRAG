from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from accounts.utils import get_active_org_member
from accounts.models import OrganizationMember


@login_required
def org_user_list(request):
    member = get_active_org_member(request.user)

    if not member or member.role != "admin":
        return HttpResponseForbidden("Admins only")

    users = (
        OrganizationMember.objects
        .select_related("user")
        .filter(organization=member.organization)
        .order_by("user__email")
    )

    return render(
        request,
        "accounts/org/users.html",
        {
            "organization": member.organization,
            "members": users,
        }
    )
