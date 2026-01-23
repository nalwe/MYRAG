from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from accounts.models import OrganizationInvite
from accounts.utils import get_active_org_member


@login_required
def invite_user(request):
    member = get_active_org_member(request.user)

    if not member or member.role != "admin":
        return HttpResponseForbidden("Admins only")

    if request.method == "POST":
        email = request.POST.get("email", "").lower().strip()

        if not email:
            messages.error(request, "Email required.")
            return redirect("org_invite")

        invite = OrganizationInvite.objects.create(
            email=email,
            organization=member.organization,
            invited_by=request.user,
            expires_at=timezone.now() + timedelta(days=7),
        )

        invite_link = request.build_absolute_uri(
            reverse("accept_invite", args=[invite.token])
        )

        send_mail(
            subject="You're invited to join " + member.organization.name,
            message=(
                f"You have been invited to join {member.organization.name}.\n\n"
                f"Click the link below to activate your account:\n\n"
                f"{invite_link}\n\n"
                f"This invite expires in 7 days."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        messages.success(request, f"Invite sent to {email}")
        return redirect("org_user_list")

    return render(request, "accounts/org/invite.html")
