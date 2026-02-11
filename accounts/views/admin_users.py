from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect

from accounts.permissions import is_org_admin
from accounts.models import Profile


# =====================================================
# 👥 ADMIN USER LIST (SUPERUSER / ORG ADMIN)
# =====================================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Q

from accounts.models import Organization, Profile


@login_required
def admin_user_list(request):
    user = request.user
    profile = user.profile

    # =================================================
    # 🔐 PERMISSIONS
    # =================================================
    if not user.is_superuser:
        return HttpResponseForbidden("Superusers only.")

    # =================================================
    # 🔍 FILTER PARAMS
    # =================================================
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    organization_id = request.GET.get("organization", "").strip()

    # =================================================
    # 👥 BASE QUERYSET
    # =================================================
    users = (
        User.objects
        .select_related("profile", "profile__organization")
        .order_by("email")
    )

    # =================================================
    # 🔎 SEARCH
    # =================================================
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    # =================================================
    # 🎭 ROLE FILTER
    # =================================================
    if role:
        users = users.filter(profile__role=role)

    # =================================================
    # 🏢 ORGANIZATION FILTER
    # =================================================
    if organization_id:
        users = users.filter(profile__organization_id=organization_id)

    # =================================================
    # 📄 RENDER (FULL OR HTMX PARTIAL)
    # =================================================
    context = {
        "users": users,
        "query": query,
        "role": role,
        "organizations": Organization.objects.all(),
        "organization_id": organization_id,
    }

    # HTMX request → return table only
    if request.headers.get("HX-Request"):
        return render(
            request,
            "accounts/admin/_user_table.html",
            context
        )

    # Normal request → full page
    return render(
        request,
        "accounts/admin/user_list.html",
        context
    )



# =====================================================
# 🔄 CHANGE USER ROLE
# =====================================================

@login_required
def admin_change_role(request, user_id):
    if not (request.user.is_superuser or is_org_admin(request.user)):
        return HttpResponseForbidden("Admins only")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        role = request.POST.get("role")

        if role not in dict(Profile.ROLE_CHOICES):
            return HttpResponseForbidden("Invalid role")

        user.profile.role = role
        user.profile.save()  # 🔥 triggers permission sync via signals

    return redirect("admin_user_list")


# =====================================================
# ⛔ ACTIVATE / DEACTIVATE USER
# =====================================================

@login_required
def admin_toggle_user(request, user_id):
    if not (request.user.is_superuser or is_org_admin(request.user)):
        return HttpResponseForbidden("Admins only")

    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        return HttpResponseForbidden("You cannot deactivate yourself")

    user.profile.is_active = not user.profile.is_active
    user.profile.save()

    return redirect("admin_user_list")


# =====================================================
# 🚫 BULK DEACTIVATE USERS (SUPERUSER ONLY)
# =====================================================

@login_required
def admin_bulk_deactivate(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Superuser only")

    if request.method == "POST":
        user_ids = request.POST.getlist("users")

        User.objects.filter(id__in=user_ids).update(is_active=False)

    return redirect("admin_user_list")
