from django.shortcuts import redirect, render
from django.urls import resolve, reverse
from django.http import HttpResponseForbidden
from django.contrib import messages

from accounts.models import Profile, OrganizationMember


class RolePermissionMiddleware:
    """
    Enforces:
    - User suspension
    - Organization suspension
    - Role-based route protection

    🔓 Superusers ALWAYS bypass everything
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # -------------------------------------------------
        # 🌍 Allow anonymous users (login, static, admin login)
        # -------------------------------------------------
        if not request.user.is_authenticated:
            return self.get_response(request)

        user = request.user

        # -------------------------------------------------
        # 🔓 ABSOLUTE SUPERUSER BYPASS
        # -------------------------------------------------
        if user.is_superuser:
            return self.get_response(request)

        # -------------------------------------------------
        # 🛠 Allow Django Admin URLs explicitly
        # -------------------------------------------------
        if request.path.startswith("/admin/"):
            return self.get_response(request)

        # -------------------------------------------------
        # 👤 Load Profile Safely
        # -------------------------------------------------
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            messages.error(request, "User profile missing.")
            return redirect(reverse("login"))

        # -------------------------------------------------
        # 🚫 USER SUSPENDED
        # -------------------------------------------------
        if not profile.is_active:
            return render(request, "accounts/suspended.html")

        # -------------------------------------------------
        # 🚫 ORGANIZATION SUSPENDED
        # -------------------------------------------------
        if profile.organization and not profile.organization.is_active:
            return render(request, "accounts/org_suspended.html")

        # -------------------------------------------------
        # 🔐 ROUTE PERMISSIONS
        # -------------------------------------------------
        try:
            resolver = resolve(request.path)
            view_name = resolver.view_name or ""
        except Exception:
            view_name = ""

        # ---- ORGANIZATION ADMIN AREA ----
        if view_name.startswith("org_"):
            if not profile.is_org_admin():
                return HttpResponseForbidden("Organization admin access only.")

        # ---- CHAT / AI AREA ----
        if view_name.startswith("chat_"):
            member = (
                OrganizationMember.objects
                .filter(user=user, is_active=True)
                .select_related("organization")
                .first()
            )

            if not member:
                return HttpResponseForbidden("AI access restricted")

            if not member.organization or not member.organization.is_active:
                return HttpResponseForbidden("Organization is inactive")

        return self.get_response(request)
