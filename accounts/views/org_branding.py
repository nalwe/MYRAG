from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect

from accounts.models import Organization


@login_required
def organization_branding(request):
    profile = request.user.profile

    if not profile.is_org_admin():
        return HttpResponseForbidden("Organization admins only.")

    organization = profile.organization

    if request.method == "POST":
        logo = request.FILES.get("logo")

        if not logo:
            return render(request, "accounts/org/branding.html", {
                "organization": organization,
                "error": "Please select a logo file.",
            })

        organization.logo = logo
        organization.save(update_fields=["logo"])

        return redirect("organization_dashboard")

    return render(request, "accounts/org/branding.html", {
        "organization": organization,
    })
