from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponseForbidden

from accounts.models import Organization, Profile


@login_required
def org_add_user(request):
    request_user = request.user
    admin_profile = request_user.profile

    # =================================================
    # 🔐 Determine Organization + Permission
    # =================================================

    # 🌍 SUPERUSER: can choose organization explicitly
    if request_user.is_superuser:
        org_id = request.GET.get("org_id")

        if not org_id:
            messages.error(request, "No organization selected.")
            return redirect("/admin/")

        organization = get_object_or_404(Organization, id=org_id)

    # 🏢 ORG ADMIN: only their own organization
    else:
        if not admin_profile.is_org_admin or not admin_profile.organization:
            return HttpResponseForbidden("Organization admin access only.")

        organization = admin_profile.organization

    # =================================================
    # 👥 Users NOT assigned to ANY organization
    # =================================================

    users = (
        User.objects
        .select_related("profile")
        .filter(
            is_superuser=False,
            profile__isnull=False,
            profile__organization__isnull=True
        )
        .order_by("email")
    )

    # =================================================
    # 📝 Handle Form Submit
    # =================================================

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        role = request.POST.get("role")

        if not user_id:
            messages.error(request, "Please select a user.")
            return redirect(request.path)

        user_to_add = get_object_or_404(User, id=user_id)
        target_profile = user_to_add.profile

        # -------------------------------------------------
        # 🔒 HARD SAFETY CHECK (SINGLE-ORG ENFORCEMENT)
        # -------------------------------------------------
        if target_profile.organization is not None:
            messages.error(
                request,
                "This user already belongs to an organization."
            )
            return redirect("organization_dashboard")

        # -------------------------------------------------
        # 🔧 ENFORCE EMAIL = USERNAME (SELF-HEALING)
        # -------------------------------------------------
        if user_to_add.email:
            normalized_email = user_to_add.email.strip().lower()
            if user_to_add.username != normalized_email:
                user_to_add.username = normalized_email
                user_to_add.save(update_fields=["username"])

        # -------------------------------------------------
        # 🔐 ROLE RESTRICTIONS
        # -------------------------------------------------

        allowed_roles = {
            Profile.ROLE_BASIC,
            Profile.ROLE_PREMIUM,
        }

        # Only superusers can assign org admins
        if request_user.is_superuser:
            allowed_roles.add(Profile.ROLE_ORG_ADMIN)

        if role not in allowed_roles:
            return HttpResponseForbidden("Invalid role assignment.")

        # -------------------------------------------------
        # ✅ Assign organization + role
        # -------------------------------------------------

        target_profile.organization = organization
        target_profile.role = role
        target_profile.is_active = True
        target_profile.save()

        messages.success(
            request,
            f"{user_to_add.email} added to {organization.name} "
            f"as {target_profile.get_role_display()}."
        )

        return redirect("organization_dashboard")

    # =================================================
    # 📄 Render
    # =================================================

    return render(
        request,
        "accounts/org/add_user.html",
        {
            "users": users,
            "organization": organization,
            "roles": Profile.ROLE_CHOICES,
        }
    )
