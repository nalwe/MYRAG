from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from django.db.models import Sum, Q
from django.core.paginator import Paginator

from accounts.models import Organization, Profile
from documents.models import Document


@login_required
def organization_dashboard(request):
    user = request.user
    profile = user.profile

    organizations = []
    organization = None
    mode = None

    # =================================================
    # 🌍 SUPERUSER MODE
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
        if not profile.is_org_admin or not profile.organization:
            return HttpResponseForbidden("Organization admins only")

        organization = profile.organization
        mode = "org_admin"

    # =================================================
    # 🔍 SEARCH
    # =================================================
    search = request.GET.get("q", "").strip()

    members_qs = (
        Profile.objects
        .select_related("user")
        .filter(organization=organization)
    )

    if search:
        members_qs = members_qs.filter(
            Q(user__email__icontains=search) |
            Q(user__username__icontains=search)
        )

    members_qs = members_qs.order_by("user__email")

    # =================================================
    # 📄 PAGINATION
    # =================================================
    paginator = Paginator(members_qs, 10)
    page_number = request.GET.get("page")
    members = paginator.get_page(page_number)

    # Preview for header/table summary
    members_preview = members_qs[:5]

    # =================================================
    # 📊 STATS
    # =================================================
    stats = {
        "users": members_qs.count(),
        "documents": Document.objects.filter(
            organization=organization
        ).count(),
        "storage": (
            Document.objects
            .filter(organization=organization)
            .aggregate(total=Sum("file_size"))["total"] or 0
        ),
    }

    # =================================================
    # 📄 DOCUMENTS
    # =================================================
    org_documents = (
        Document.objects
        .filter(organization=organization)
        .order_by("-created_at")[:10]
    )

    global_documents = (
        Document.objects
        .filter(is_public=True, organization__isnull=True)
        .order_by("-created_at")[:10]
    )

    return render(
        request,
        "accounts/org/dashboard.html",
        {
            "organization": organization,
            "organizations": organizations,
            "stats": stats,
            "members": members,              # paginated
            "members_preview": members_preview,
            "org_documents": org_documents,
            "global_documents": global_documents,
            "mode": mode,
            "search": search,
            "empty_state": False,
        },
    )



