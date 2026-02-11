import csv
from io import TextIOWrapper

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from accounts.models import Organization
from accounts.utils import get_active_org_member


@login_required
def org_bulk_add_users(request):

    # ------------------------------------------
    # Determine Organization
    # ------------------------------------------
    if request.user.is_superuser:
        org_id = request.GET.get("org_id")
        if not org_id:
            messages.error(request, "No organization selected.")
            return redirect("organization_dashboard")

        organization = get_object_or_404(Organization, id=org_id)

    else:
        member = get_active_org_member(request.user)

        if not member or not member.is_admin():
            messages.error(request, "Permission denied.")
            return redirect("organization_dashboard")

        organization = member.organization

    # ------------------------------------------
    # Handle Upload
    # ------------------------------------------
    if request.method == "POST":

        file = request.FILES.get("file")

        if not file:
            messages.error(request, "Please upload a CSV file.")
            return redirect(request.path)

        decoded_file = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(decoded_file)

        created = 0
        skipped = 0

        for row in reader:

            email = row.get("email")
            role = row.get("role", OrganizationMember.ROLE_MEMBER)

            if not email:
                skipped += 1
                continue

            user, _ = User.objects.get_or_create(
                username=email,
                defaults={"email": email}
            )

            # Prevent duplicate membership
            if OrganizationMember.objects.filter(
                user=user,
                organization=organization
            ).exists():
                skipped += 1
                continue

            OrganizationMember.objects.create(
                user=user,
                organization=organization,
                role=role
            )

            created += 1

        messages.success(
            request,
            f"{created} users added. {skipped} skipped."
        )

        return redirect("org_user_list")

    return render(
        request,
        "accounts/org_bulk_add_users.html",
        {"organization": organization}
    )
