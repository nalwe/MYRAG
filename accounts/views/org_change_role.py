from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseForbidden

from accounts.models import Profile





@login_required
def org_change_role(request, profile_id):
    admin = request.user.profile

    if not admin.is_org_admin:
        return HttpResponseForbidden()

    member = get_object_or_404(
        Profile,
        id=profile_id,
        organization=admin.organization
    )

    role = request.POST.get("role")

    allowed_roles = {
        Profile.ROLE_BASIC,
        Profile.ROLE_PREMIUM,
    }

    if role not in allowed_roles:
        return HttpResponseForbidden("Invalid role.")

    member.role = role
    member.save()

    return redirect("organization_dashboard")