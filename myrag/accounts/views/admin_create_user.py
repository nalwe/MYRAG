from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages

from accounts.models import Organization, OrganizationMember, Profile


def superuser_required(user):
    return user.is_superuser


@user_passes_test(superuser_required)
def admin_create_user(request):

    organizations = Organization.objects.order_by("name")

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        org_id = request.POST.get("organization")
        role = request.POST.get("role")

        if not all([email, password, org_id, role]):
            messages.error(request, "All fields required.")
            return redirect("admin_create_user")

        organization = get_object_or_404(Organization, id=org_id)

        # ----------------------------------
        # Create / Get User
        # ----------------------------------
        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email}
        )

        if created:
            user.set_password(password)
            user.save()

        # ----------------------------------
        # Assign Profile Role
        # ----------------------------------
        profile = user.profile
        profile.organization = organization
        profile.role = role
        profile.save()

        # ----------------------------------
        # Determine Membership Role
        # ----------------------------------
        if role == Profile.ROLE_ORG_ADMIN:
            membership_role = OrganizationMember.ROLE_ADMIN
        else:
            membership_role = OrganizationMember.ROLE_MEMBER

        # ----------------------------------
        # Create Membership
        # ----------------------------------
        OrganizationMember.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={"role": membership_role}
        )

        messages.success(request, "User created successfully.")
        return redirect("admin_dashboard")

    return render(
        request,
        "accounts/admin/create_user.html",
        {"organizations": organizations}
    )
