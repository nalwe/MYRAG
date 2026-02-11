# accounts/middleware.py

from django.shortcuts import redirect, render
from django.urls import resolve
from django.http import HttpResponseForbidden
from django.contrib import messages

from accounts.models import Profile, OrganizationMember


class RolePermissionMiddleware:
    """
    Enforces:
    - User suspension
    - Organization suspension
    - Forced password change
    - Role-based route protection

    Superusers bypass all restrictions.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # --------------------------------------------------
        # Allow anonymous users
        # --------------------------------------------------
        if not request.user.is_authenticated:
            return self.get_response(request)

        user = request.user

        # --------------------------------------------------
        # SUPERUSER BYPASS
        # --------------------------------------------------
        if user.is_superuser:
            return self.get_response(request)

        # --------------------------------------------------
        # Load Profile
        # --------------------------------------------------
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            messages.error(request, "User profile missing.")
            return redirect("document_list")

        resolver = resolve(request.path)
        view_name = resolver.view_name or ""

        # --------------------------------------------------
        # FORCE PASSWORD CHANGE
        # --------------------------------------------------
        allowed_password_views = {
            "password_change",
            "password_change_done",
            "logout",
        }

        if profile.must_change_password and view_name not in allowed_password_views:
            messages.warning(
                request,
                "You must change your password before continuing."
            )
            return redirect("password_change")

        # --------------------------------------------------
        # USER SUSPENDED
        # --------------------------------------------------
        if not profile.is_active:
            return render(
                request,
                "accounts/suspended.html",
                status=403
            )

        # --------------------------------------------------
        # ORGANIZATION SUSPENDED
        # --------------------------------------------------
        if profile.organization and not profile.organization.is_active:
            return render(
                request,
                "accounts/org_suspended.html",
                status=403
            )

        # --------------------------------------------------
        # DJANGO ADMIN
        # --------------------------------------------------
        if request.path.startswith("/admin/"):
            return HttpResponseForbidden("Superuser access only.")

        # --------------------------------------------------
        # PLATFORM ADMIN
        # --------------------------------------------------
        if request.path.startswith("/accounts/admin/"):
            return HttpResponseForbidden("Superuser access only.")

        # --------------------------------------------------
        # ORGANIZATION ADMIN ROUTES
        # --------------------------------------------------
        if request.path.startswith("/accounts/org/"):
            if not profile.is_org_admin:
                return HttpResponseForbidden(
                    "Organization admin access only."
                )

        # --------------------------------------------------
        # CHAT / AI ACCESS
        # --------------------------------------------------
        if view_name.startswith("chat_"):
            member = (
                OrganizationMember.objects
                .filter(user=user, is_active=True)
                .select_related("organization")
                .first()
            )

            if not member:
                messages.warning(
                    request,
                    "Join an organization to use AI features."
                )
                return redirect("document_list")

            if not member.organization or not member.organization.is_active:
                return HttpResponseForbidden("Organization inactive")

        return self.get_response(request)
