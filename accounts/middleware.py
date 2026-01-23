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
    Superusers always bypass all restrictions.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # -------------------------------------------------
        # 🌍 Allow anonymous access (login, static, etc)
        # -------------------------------------------------
        if not request.user.is_authenticated:
            return self.get_response(request)

        user = request.user

        # -------------------------------------------------
        # 🔓 SUPERUSER BYPASS (ABSOLUTE)
        # -------------------------------------------------
        if user.is_superuser:
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
        # 🚫 ORGANIZATION SUSPENDED (Profile-based)
        # -------------------------------------------------
        if profile.organization and not profile.organization.is_active:
            return render(request, "accounts/org_suspended.html")

        # -------------------------------------------------
        # 🔐 ROUTE PERMISSIONS
        # -------------------------------------------------
        resolver = resolve(request.path)
        view_name = resolver.view_name or ""

        # ---- SUPERUSER AREA ----
        if view_name.startswith("admin_"):
            return HttpResponseForbidden("Superuser access only.")

        # ---- ORGANIZATION ADMIN AREA ----
        if view_name.startswith("org_"):
            if not profile.is_org_admin():
                return HttpResponseForbidden("Organization admin access only.")

        # ---- CHAT / AI AREA (OrganizationMember-based) ----
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
