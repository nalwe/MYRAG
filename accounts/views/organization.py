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
from accounts.utils import is_org_admin, can_add_admin
from documents.models import Document


# =====================================================
# 🔐 PLATFORM ADMIN HELPERS
# =====================================================

def is_platform_admin(user):
    return user.is_superuser or user.is_staff


def get_active_org_member(user):
    return (
        OrganizationMember.objects
        .filter(user=user, is_active=True)
        .select_related("organization")
        .first()
    )


# =====================================================
# 👤 CREATE ORGANIZATION ADMIN (SUPERUSER ONLY)
# =====================================================

@login_required
def create_org_admin(request, org_id):

    if not request.user.is_superuser:
        return HttpResponseForbidden("Superuser only.")

    organization = get_object_or_404(Organization, id=org_id)

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        if not email or not password:
            return render(request, "accounts/admin/create_org_admin.html", {
                "organization": organization,
                "error": "Email and password are required."
            })

        if User.objects.filter(username=email).exists():
            return render(request, "accounts/admin/create_org_admin.html", {
                "organization": organization,
                "error": "User already exists."
            })

        # ✅ Create user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
        )

        # ✅ Update profile
        profile = user.profile
        profile.role = Profile.ROLE_ORG_ADMIN
        profile.organization = organization
        profile.save()

        # ✅ Create organization membership
        OrganizationMember.objects.create(
            user=user,
            organization=organization,
            role=OrganizationMember.ROLE_ADMIN,
        )

        AuditLog.objects.create(
            actor=request.user,
            action="Created organization admin",
            target=f"{email} @ {organization.name}",
        )

        return redirect("organization_dashboard")

    return render(request, "accounts/admin/create_org_admin.html", {
        "organization": organization
    })


# ✅ Backward compatibility for old imports
create_org_user = create_org_admin


# =====================================================
# ➕ CREATE COMPANY USER
# =====================================================

@login_required
def create_company_user(request):
    user = request.user
    is_superuser = is_platform_admin(user)

    # =========================
    # 🔐 PERMISSION CHECK
    # =========================
    member = get_active_org_member(user)

    if not (is_superuser or (member and member.is_admin())):
        return HttpResponseForbidden("Admins only")

    # =========================
    # 🏢 DETERMINE ORGANIZATION
    # =========================
    if is_superuser:
        # Superuser must belong to at least one org to create users
        organization = member.organization if member else None
    else:
        organization = member.organization

    if not organization or not organization.is_active:
        return HttpResponseForbidden("Invalid or inactive organization.")

    # =========================
    # 📝 HANDLE FORM SUBMIT
    # =========================
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        role = request.POST.get("role", OrganizationMember.ROLE_MEMBER)

        # -------------------------
        # Validation
        # -------------------------
        if not username or not password:
            return render(request, "accounts/create_user.html", {
                "error": "Username and password are required.",
            })

        if User.objects.filter(username=username).exists():
            return render(request, "accounts/create_user.html", {
                "error": "Username already exists.",
            })

        if role not in (
            OrganizationMember.ROLE_ADMIN,
            OrganizationMember.ROLE_MEMBER,
        ):
            return render(request, "accounts/create_user.html", {
                "error": "Invalid role selected.",
            })

        # -------------------------
        # Create user
        # -------------------------
        new_user = User.objects.create_user(
            username=username,
            password=password,
        )

        # -------------------------
        # Attach to organization
        # -------------------------
        OrganizationMember.objects.create(
            user=new_user,
            organization=organization,
            role=role,
        )

        AuditLog.objects.create(
            actor=request.user,
            action="Created company user",
            target=f"{username} @ {organization.name}",
        )

        return redirect("company_users")

    # =========================
    # 📄 Render form
    # =========================
    return render(request, "accounts/create_user.html")


# =====================================================
# 👥 COMPANY USERS LIST
# =====================================================

@login_required
def company_users(request):
    # 🔐 Permission
    if not (is_platform_admin(request.user) or is_org_admin(request.user)):
        return HttpResponseForbidden("Admins only")

    # =================================================
    # 🧠 SUPERUSER MODE (no membership required)
    # =================================================
    if request.user.is_superuser:
        # Pick first organization if any exist
        admin_member = (
            OrganizationMember.objects
            .select_related("organization")
            .first()
        )

        # If no members exist yet — show empty screen safely
        if not admin_member:
            return render(request, "accounts/company_users.html", {
                "members": [],
                "organization": None,
                "empty_state": True,
            })

    # =================================================
    # 🧑 ORG ADMIN MODE
    # =================================================
    else:
        admin_member = (
            OrganizationMember.objects
            .filter(
                user=request.user,
                role=OrganizationMember.ROLE_ADMIN,
                is_active=True
            )
            .select_related("organization")
            .first()
        )

        if not admin_member:
            return HttpResponseForbidden("Organization access error")

    # =================================================
    # 👥 Load members
    # =================================================
    members = (
        OrganizationMember.objects
        .filter(organization=admin_member.organization)
        .select_related("user")
        .order_by("-role", "user__username")
    )

    return render(request, "accounts/company_users.html", {
        "members": members,
        "organization": admin_member.organization,
        "empty_state": False,
    })



# =====================================================
# 🔄 TOGGLE ADMIN ROLE
# =====================================================

@login_required
def toggle_admin(request, member_id):
    if not (is_platform_admin(request.user) or is_org_admin(request.user)):
        return HttpResponseForbidden()

    member = OrganizationMember.objects.select_related("organization").get(id=member_id)

    if member.role == OrganizationMember.ROLE_ADMIN:
        member.role = OrganizationMember.ROLE_MEMBER
    else:
        if not can_add_admin(member.organization):
            return HttpResponseForbidden("Admin limit reached")
        member.role = OrganizationMember.ROLE_ADMIN

    member.save(update_fields=["role"])
    return redirect("company_users")


# =====================================================
# ⛔ DEACTIVATE USER
# =====================================================

@login_required
def deactivate_user(request, member_id):
    if not (is_platform_admin(request.user) or is_org_admin(request.user)):
        return HttpResponseForbidden()

    member = OrganizationMember.objects.select_related("user").get(id=member_id)

    if member.user == request.user:
        return HttpResponseForbidden("Cannot deactivate yourself")

    member.user.is_active = False
    member.user.save(update_fields=["is_active"])

    return redirect("company_users")


# =====================================================
# 📊 COMPANY DASHBOARD
# =====================================================



@login_required
def company_dashboard(request):
    profile = request.user.profile

    # 🔐 Only organization admins allowed here
    if not profile.is_org_admin():
        return HttpResponseForbidden("Organization admins only.")

    organization = profile.organization

    if not organization:
        return HttpResponseForbidden("No organization assigned.")

    # =================================================
    # 👥 ORGANIZATION USERS
    # =================================================
    members = (
        Profile.objects
        .filter(organization=organization)
        .select_related("user")
        .order_by("role", "user__date_joined")
    )

    # =================================================
    # 📄 DOCUMENTS
    # =================================================

    # Organization documents
    org_documents = Document.objects.filter(
        organization=organization
    ).order_by("-created_at")

    # 🌍 Global public documents (superuser uploads)
    global_documents = Document.objects.filter(
        organization__isnull=True,
        owner__isnull=True,
        is_public=True,
    ).order_by("-created_at")

    # =================================================
    # 💾 STORAGE STATS
    # =================================================
    total_storage = (
        Document.objects
        .filter(organization=organization)
        .aggregate(total=Sum("file_size"))["total"] or 0
    )

    # =================================================
    # 📈 API USAGE
    # =================================================
    api_used = organization.api_tokens_used
    api_limit = organization.api_token_limit

    usage_percent = (
        int((api_used / api_limit) * 100)
        if api_limit else 0
    )

    # =================================================
    # 📦 CONTEXT
    # =================================================
    context = {
        "organization": organization,
        "members": members,
        "org_documents": org_documents,
        "global_documents": global_documents,
        "total_storage": total_storage,

        "api_used": api_used,
        "api_limit": api_limit,
        "usage_percent": usage_percent,
    }

    return render(
        request,
        "accounts/org/dashboard.html",
        context,
    )




# =====================================================
# ♻️ REACTIVATE USER
# =====================================================

@login_required
def reactivate_user(request, member_id):
    if not (is_platform_admin(request.user) or is_org_admin(request.user)):
        return HttpResponseForbidden("Admins only")

    member = get_object_or_404(
        OrganizationMember.objects.select_related("user", "organization"),
        id=member_id
    )

    admin_member = get_active_org_member(request.user)

    if not admin_member or member.organization != admin_member.organization:
        return HttpResponseForbidden("Not your organization")

    member.user.is_active = True
    member.user.save(update_fields=["is_active"])

    return redirect("company_users")


# =====================================================
# 🏢 CREATE ORGANIZATION (SUPERUSER)
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
                "error": "Organization name is required."
            })

        if Organization.objects.filter(name__iexact=name).exists():
            return render(request, "accounts/create_organization.html", {
                "error": "An organization with this name already exists."
            })

        org = Organization.objects.create(
            name=name,
            max_users=max_users,
            api_token_limit=api_limit,
        )

        AuditLog.objects.create(
            actor=request.user,
            action="Created organization",
            target=org.name,
        )

        return redirect("create_org_admin", org_id=org.id)

    return render(request, "accounts/create_organization.html")


# =====================================================
# 📋 ORGANIZATION LIST (SUPERUSER)
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
# 🔁 TOGGLE ORGANIZATION STATUS (SUPERUSER)
# =====================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_org(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    org.is_active = not org.is_active
    org.save(update_fields=["is_active"])

    AuditLog.objects.create(
        actor=request.user,
        action="Toggled organization status",
        target=org.name,
    )

    return redirect("organization_list")


# =====================================================
# 📈 ORGANIZATION USAGE (SUPERUSER)
# =====================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def organization_usage(request, org_id):
    org = get_object_or_404(Organization, id=org_id)

    stats = {
        "users": OrganizationMember.objects.filter(organization=org).count(),
        "documents": Document.objects.filter(organization=org).count(),
        "storage": (
            Document.objects
            .filter(organization=org)
            .aggregate(total=Sum("file_size"))["total"] or 0
        ),
    }

    return render(request, "accounts/organization_usage.html", {
        "organization": org,
        "stats": stats,
    })
