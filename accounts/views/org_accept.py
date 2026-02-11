from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone

from accounts.models import OrganizationInvite


def accept_invite(request, token):
    invite = get_object_or_404(
        OrganizationInvite,
        token=token,
        is_used=False,
    )

    if invite.is_expired():
        messages.error(request, "Invite expired.")
        return redirect("login")

    if request.method == "POST":
        password = request.POST.get("password")

        user, _ = User.objects.get_or_create(
            username=invite.email,
            defaults={"email": invite.email},
        )
        user.set_password(password)
        user.save()

        OrganizationMember.objects.get_or_create(
            user=user,
            organization=invite.organization,
            defaults={"role": "member", "tier": "basic"},
        )

        invite.is_used = True
        invite.save()

        messages.success(request, "Account activated. Please login.")
        return redirect("login")

    return render(
        request,
        "accounts/org/accept_invite.html",
        {"invite": invite}
    )
