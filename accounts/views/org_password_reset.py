from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden

from accounts.utils import is_org_admin, get_active_org_member


@login_required
def org_admin_reset_password(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    # 1️⃣ Must be org admin
    if not is_org_admin(request.user):
        return HttpResponseForbidden("Permission denied.")

    # 2️⃣ Must be same organization
    admin_member = get_active_org_member(request.user)
    target_member = get_active_org_member(target_user)

    if not admin_member or not target_member:
        return HttpResponseForbidden("Invalid organization.")

    if admin_member.organization != target_member.organization:
        return HttpResponseForbidden("Cross-organization action forbidden.")

    # 3️⃣ Normal password reset logic
    if request.method == "POST":
        form = SetPasswordForm(target_user, request.POST)

        if form.is_valid():
            form.save()

            if hasattr(target_user, "profile"):
                target_user.profile.must_change_password = True
                target_user.profile.save(update_fields=["must_change_password"])

            messages.success(request, "Password reset successfully.")
            return redirect("org_user_list")

    else:
        form = SetPasswordForm(target_user)

    return render(
        request,
        "accounts/org_reset_password.html",
        {
            "form": form,
            "target_user": target_user,
        },
    )
