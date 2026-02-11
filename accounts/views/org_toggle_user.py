from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponseForbidden

from accounts.models import Organization, Profile





@login_required
def org_toggle_user(request, profile_id):
    admin_profile = request.user.profile

    if not admin_profile.is_org_admin:
        return redirect("dashboard")

    member = get_object_or_404(
        Profile,
        id=profile_id,
        organization=admin_profile.organization
    )

    if member.user == request.user:
        return redirect("org_dashboard")  # prevent self-lockout

    member.is_active = not member.is_active
    member.save()

    return redirect("organization_dashboard")
