from django.urls import path
from django.contrib.auth import views as auth_views
from accounts.views.org_password_reset import org_admin_reset_password
from accounts.views.org_add_user import org_add_user
from accounts.views.org_bulk_add_users import org_bulk_add_users
from accounts.views.admin_create_user import admin_create_user
from accounts.views.user_views import create_user



from accounts.views.org_users import org_user_list
from accounts.views.org_invite import invite_user
from accounts.views.org_accept import accept_invite






# =========================
# 🔐 AUTH
# =========================
from accounts.views.auth_views import (
    login_view,
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
    create_org_admin,
    create_company_user,
    company_users,
    organization_dashboard,
    create_organization,
    organization_list,
    toggle_org,
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
    # 🔐 AUTHENTICATION
    # =====================================================
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),

    # =====================================================
    # 🔑 PASSWORD RESET
    # =====================================================
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html"
        ),
        name="password_reset",
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # =====================================================
    # 🌍 SUPERUSER ADMIN
    # =====================================================
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),

    # ---- Organizations ----
    path("admin/organizations/create/", create_organization, name="create_organization"),
    path("admin/organizations/", organization_list, name="organization_list"),
    

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

    # ---- Org Users ----
    path("org/users/", org_user_list, name="org_user_list"),
    path("org/invite/", invite_user, name="org_invite"),
    path("org/invite/<uuid:token>/", accept_invite, name="accept_invite"),

    path(
    "org/users/<int:user_id>/reset-password/",
    org_admin_reset_password,
    name="org_admin_reset_password",
),

path(
    "org/users/add/",
    org_add_user,
    name="org_add_user"
),

path("org/users/bulk-add/", org_bulk_add_users, name="org_bulk_add_users"),
path("admin/create-user/", admin_create_user, name="admin_create_user"),
path("users/create/", create_user, name="create_user"),
# accounts/urls.py


]


