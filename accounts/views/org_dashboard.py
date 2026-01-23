from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden

from accounts.models import Organization, OrganizationMember
from accounts.utils import get_active_org_member
from documents.models import Document
from django.db.models import Sum


@login_required
def organization_dashboard(request):
    user = request.user

    organizations = []   # for superuser dropdown
    organization = None
    mode = None

    # =================================================
    # 🌍 SUPERUSER MODE — CAN VIEW ANY ORG
    # =================================================
    if user.is_superuser:
        org_id = request.GET.get("org_id")

        organizations = Organization.objects.order_by("name")

        if org_id:
            organization = get_object_or_404(Organization, id=org_id)
        else:
            organization = organizations.first()

        if not organization:
            return render(
                request,
                "accounts/org/dashboard.html",
                {
                    "organization": None,
                    "organizations": [],
                    "empty_state": True,
                    "mode": "superuser",
                },
            )

        mode = "superuser"

    # =================================================
    # 🏢 ORG ADMIN MODE
    # =================================================
    else:
        member = get_active_org_member(user)

        if not member or member.role != "admin":
            return HttpResponseForbidden("Organization admins only")

        organization = member.organization
        mode = "org_admin"

    # =================================================
    # 📊 DASHBOARD DATA
    # =================================================

    stats = {
        "users": OrganizationMember.objects.filter(
            organization=organization
        ).count(),

        "documents": Document.objects.filter(
            organization=organization
        ).count(),

        "storage": (
            Document.objects
            .filter(organization=organization)
            .aggregate(total=Sum("file_size"))["total"] or 0
        ),
    }

    org_documents = (
        Document.objects
        .filter(organization=organization)
        .order_by("-created_at")[:10]
    )

    global_documents = (
        Document.objects
        .filter(
            is_public=True,
            organization__isnull=True,
        )
        .order_by("-created_at")[:10]
    )

    members = (
        OrganizationMember.objects
        .select_related("user")
        .filter(organization=organization)
        .order_by("user__email")
    )

    return render(
        request,
        "accounts/org/dashboard.html",
        {
            "organization": organization,
            "organizations": organizations,   # 👈 for dropdown
            "stats": stats,
            "members": members,
            "org_documents": org_documents,
            "global_documents": global_documents,
            "mode": mode,
            "empty_state": False,
        },
    )
