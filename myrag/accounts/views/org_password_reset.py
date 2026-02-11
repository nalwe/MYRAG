from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.models import User

from accounts.models import Profile


@login_required
def org_admin_reset_password(request, user_id):

    target_user = get_object_or_404(User, id=user_id)

    # Ensure admin permission
    if not request.user.profile.is_org_admin:
        messages.error(request, "Permission denied.")
        return redirect("org_user_list")

    if request.method == "POST":
        form = SetPasswordForm(target_user, request.POST)

        if form.is_valid():
            form.save()

            # Force password change on next login
            target_user.profile.must_change_password = True
            target_user.profile.save()

            messages.success(request, "Password reset successfully.")
            return redirect("org_user_list")

    else:
        form = SetPasswordForm(target_user)

    return render(
        request,
        "accounts/org_reset_password.html",
        {
            "form": form,
            "target_user": target_user
        }
    )
