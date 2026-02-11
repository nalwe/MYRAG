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

@login_required
def admin_user_list(request):
    if not (request.user.is_superuser or is_org_admin(request.user)):
        return HttpResponseForbidden("Admins only")

    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    page_number = request.GET.get("page", 1)

    users = User.objects.select_related("profile").order_by("username")

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    if role:
        users = users.filter(profile__role=role)

    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(page_number)

    template = (
        "accounts/admin/_user_table.html"
        if request.headers.get("HX-Request")
        else "accounts/admin/user_list.html"
    )

    return render(request, template, {
        "page_obj": page_obj,
        "query": query,
        "role": role,
        "role_choices": Profile.ROLE_CHOICES,
    })


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
