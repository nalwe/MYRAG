from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from accounts.permissions import is_admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect

@login_required
def admin_user_list(request):
    if not is_admin(request.user):
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

    paginator = Paginator(users, 10)  # 👈 10 users per page
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
    })



@login_required
def admin_change_role(request, user_id):
    if not is_admin(request.user):
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        role = request.POST.get("role")
        user.profile.role = role
        user.profile.save()

    return redirect("admin_user_list")

@login_required
def admin_toggle_user(request, user_id):
    if not is_admin(request.user):
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)
    user.profile.is_active = not user.profile.is_active
    user.profile.save()

    return redirect("admin_user_list")


@login_required
def admin_bulk_deactivate(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("Admins only")

    if request.method == "POST":
        user_ids = request.POST.getlist("users")
        User.objects.filter(id__in=user_ids).update(is_active=False)

    return redirect("admin_user_list")

