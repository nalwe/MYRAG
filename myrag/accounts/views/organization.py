from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import (
    Organization,
    OrganizationMember,
    AuditLog,
    Profile,
)
from accounts.utils import is_org_admin, get_user_organization
from documents.models import Document


# =====================================================
# 🔐 PLATFORM ADMIN (SUPERUSER ONLY)
# =====================================================

def is_platform_admin(user):
    return user.is_superuser


# =====================================================
# 👤 CREATE ORGANISATION ADMIN (SUPERUSER ONLY)
# =====================================================

@login_required
def create_org_admin(request, org_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Superuser only.")

    organization = get_object_or_404(Organization, id=org_id)

    # Enforce ONE org admin
    if Profile.objects.filter(
        organization=organization,
        role=Profile.ROLE_ORG_ADMIN,
        is_active=True,
    ).exists():
        return HttpResponseForbidden("Organisation admin already exists.")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        if not email or not password:
            return render(request, "accounts/admin/create_org_admin.html", {
                "organization": organization,
                "error": "Email and password are required.",
            })

        if User.objects.filter(username=email).exists():
            return render(request, "accounts/admin/create_org_admin.html", {
                "organization": organization,
                "error": "User already exists.",
            })

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
        )

        profile = user.profile
        profile.role = Profile.ROLE_ORG_ADMIN
        profile.organization = organization
        profile.save()

        OrganizationMember.objects.create(
            user=user,
            organization=organization,
            is_active=True,
        )

        AuditLog.objects.create(
            actor=request.user,
            action="Created organisation admin",
            target=f"{email} @ {organization.name}",
        )

        return redirect("organization_dashboard")

    return render(request, "accounts/admin/create_org_admin.html", {
        "organization": organization,
    })


# Backward compatibility
create_org_user = create_org_admin


# =====================================================
# ➕ CREATE ORGANISATION USER (ORG ADMIN / SUPERUSER)
# =====================================================

@login_required
def create_company_user(request):
    user = request.user

    if not (user.is_superuser or is_org_admin(user)):
        return HttpResponseForbidden("Admins only.")

    organization = (
        get_user_organization(user)
        if not user.is_superuser
        else Organization.objects.first()
    )

    if not organization or not organization.is_active:
        return HttpResponseForbidden("Invalid or inactive organisation.")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        role = request.POST.get("role", Profile.ROLE_BASIC)

        if not username or not password:
            return render(request, "accounts/create_user.html", {
                "error": "Username and password are required.",
            })

        if User.objects.filter(username=username).exists():
            return render(request, "accounts/create_user.html", {
                "error": "Username already exists.",
            })

        if role not in (
            Profile.ROLE_BASIC,
            Profile.ROLE_PREMIUM,
        ):
            return render(request, "accounts/create_user.html", {
                "error": "Invalid role selected.",
            })

        new_user = User.objects.create_user(
            username=username,
            password=password,
        )

        new_user.profile.role = role
        new_user.profile.organization = organization
        new_user.profile.save()

        OrganizationMember.objects.create(
            user=new_user,
            organization=organization,
            is_active=True,
        )

        AuditLog.objects.create(
            actor=request.user,
            action="Created organisation user",
            target=f"{username} @ {organization.name}",
        )

        return redirect("company_users")

    return render(request, "accounts/create_user.html")


# =====================================================
# 👥 ORGANISATION USERS LIST
# =====================================================

@login_required
def company_users(request):
    if not (request.user.is_superuser or is_org_admin(request.user)):
        return HttpResponseForbidden("Admins only.")

    organization = (
        get_user_organization(request.user)
        if not request.user.is_superuser
        else Organization.objects.first()
    )

    if not organization:
        return render(request, "accounts/company_users.html", {
            "members": [],
            "organization": None,
            "empty_state": True,
        })

    members = (
        Profile.objects
        .filter(organization=organization)
        .select_related("user")
        .order_by("role", "user__username")
    )

    return render(request, "accounts/company_users.html", {
        "members": members,
        "organization": organization,
        "empty_state": False,
    })


# =====================================================
# ⛔ DEACTIVATE USER
# =====================================================

@login_required
def deactivate_user(request, user_id):
    if not (request.user.is_superuser or is_org_admin(request.user)):
        return HttpResponseForbidden("Admins only.")

    target = get_object_or_404(User, id=user_id)

    if target == request.user:
        return HttpResponseForbidden("Cannot deactivate yourself.")

    target.is_active = False
    target.save(update_fields=["is_active"])

    return redirect("company_users")


# =====================================================
# ♻️ REACTIVATE USER
# =====================================================

@login_required
def reactivate_user(request, user_id):
    if not (request.user.is_superuser or is_org_admin(request.user)):
        return HttpResponseForbidden("Admins only.")

    target = get_object_or_404(User, id=user_id)
    target.is_active = True
    target.save(update_fields=["is_active"])

    return redirect("company_users")


# =====================================================
# 📊 ORGANISATION DASHBOARD
# =====================================================

@login_required
def company_dashboard(request):
    profile = request.user.profile

    if not profile.is_org_admin:
        return HttpResponseForbidden("Organisation admins only.")

    organization = profile.organization
    if not organization:
        return HttpResponseForbidden("No organisation assigned.")

    members = (
        Profile.objects
        .filter(organization=organization)
        .select_related("user")
        .order_by("role", "user__date_joined")
    )

    org_documents = Document.objects.filter(
        organization=organization
    ).order_by("-created_at")

    global_documents = Document.objects.filter(
        organization__isnull=True,
        uploaded_by__isnull=True,
        is_public=True,
    ).order_by("-created_at")

    total_storage = (
        Document.objects
        .filter(organization=organization)
        .aggregate(total=Sum("file_size"))["total"] or 0
    )

    api_used = organization.api_tokens_used
    api_limit = organization.api_token_limit
    usage_percent = int((api_used / api_limit) * 100) if api_limit else 0

    return render(
        request,
        "accounts/org/dashboard.html",
        {
            "organization": organization,
            "members": members,
            "org_documents": org_documents,
            "global_documents": global_documents,
            "total_storage": total_storage,
            "api_used": api_used,
            "api_limit": api_limit,
            "usage_percent": usage_percent,
        },
    )


# =====================================================
# 🏢 CREATE ORGANISATION (SUPERUSER)
# =====================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def create_organization(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        max_users = request.POST.get("max_users", 10)
        api_limit = request.POST.get("api_token_limit", 1_000_000)

        if not name:
            return render(request, "accounts/create_organization.html", {
                "error": "Organisation name is required.",
            })

        if Organization.objects.filter(name__iexact=name).exists():
            return render(request, "accounts/create_organization.html", {
                "error": "An organisation with this name already exists.",
            })

        org = Organization.objects.create(
            name=name,
            max_users=max_users,
            api_token_limit=api_limit,
        )

        AuditLog.objects.create(
            actor=request.user,
            action="Created organisation",
            target=org.name,
        )

        return redirect("create_org_admin", org_id=org.id)

    return render(request, "accounts/create_organization.html")


# =====================================================
# 📋 ORGANISATION LIST (SUPERUSER)
# =====================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def organization_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    orgs = Organization.objects.all().order_by("name")

    if q:
        orgs = orgs.filter(name__icontains=q)

    if status == "active":
        orgs = orgs.filter(is_active=True)
    elif status == "archived":
        orgs = orgs.filter(is_active=False)

    return render(request, "accounts/organization_list.html", {
        "organizations": orgs,
        "q": q,
        "status": status,
    })


# =====================================================
# 🔁 TOGGLE ORGANISATION STATUS (SUPERUSER)
# =====================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_org(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    org.is_active = not org.is_active
    org.save(update_fields=["is_active"])

    AuditLog.objects.create(
        actor=request.user,
        action="Toggled organisation status",
        target=org.name,
    )

    return redirect("organization_list")
