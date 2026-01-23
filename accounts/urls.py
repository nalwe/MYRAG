from django.urls import path
from accounts.views.org_users import org_user_list
from accounts.views.org_invite import invite_user
from accounts.views.org_accept import accept_invite

# =========================
# 🔐 AUTH
# =========================
from accounts.views.auth_views import (
    login_view,
    verify_otp,
    logout_view,
)


# =========================
# 🌍 SUPERUSER ADMIN
# =========================
from accounts.views.admin_dashboard import (
    admin_dashboard,
    audit_log,
)

from accounts.views.organization import (
    create_organization,
    organization_list,
    toggle_org,
    organization_usage,
    create_org_admin,
)

from accounts.views.admin_users import (
    admin_user_list,
    admin_change_role,
    admin_toggle_user,
    admin_bulk_deactivate,
)

# =========================
# 🏢 ORGANIZATION ADMIN
# =========================
from accounts.views.org_dashboard import organization_dashboard
from accounts.views.org_branding import organization_branding


urlpatterns = [

    # =====================================================
    # 🔐 AUTHENTICATION (OTP)
    # =====================================================
    path("login/", login_view, name="login"),
    path("verify-otp/", verify_otp, name="verify_otp"),
    path("logout/", logout_view, name="logout"),

    # =====================================================
    # 🌍 SUPERUSER ADMIN
    # =====================================================
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),

    # ---- Organizations ----
    path("admin/organizations/create/", create_organization, name="create_organization"),
    path("admin/organizations/", organization_list, name="organization_list"),
    path("admin/organizations/<int:org_id>/toggle/", toggle_org, name="toggle_org"),
    path("admin/organizations/<int:org_id>/usage/", organization_usage, name="organization_usage"),

    # ---- Create Org Admin ----
    path("admin/org-admin/create/<int:org_id>/", create_org_admin, name="create_org_admin"),

    # ---- Users ----
    path("admin/users/", admin_user_list, name="admin_user_list"),
    path("admin/users/<int:user_id>/role/", admin_change_role, name="admin_change_role"),
    path("admin/users/<int:user_id>/toggle/", admin_toggle_user, name="admin_toggle_user"),
    path("admin/users/bulk-deactivate/", admin_bulk_deactivate, name="admin_bulk_deactivate"),

    # ---- Audit ----
    path("admin/audit-log/", audit_log, name="audit_log"),

    # =====================================================
    # 🏢 ORGANIZATION ADMIN DASHBOARD
    # =====================================================
    path("org/dashboard/", organization_dashboard, name="organization_dashboard"),
    path("org/branding/", organization_branding, name="org_branding"),

    #INVITE CODE
    path("org/users/", org_user_list, name="org_user_list"),
    path("org/invite/", invite_user, name="org_invite"),
    path("org/invite/<uuid:token>/", accept_invite, name="accept_invite"),
]






