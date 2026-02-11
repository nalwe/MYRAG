from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login as auth_login, logout


from accounts.models import Profile


# =====================================================
# 🔐 LOGIN (EMAIL + PASSWORD)
# =====================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect_after_login(request.user)

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, "accounts/login.html")

        user = authenticate(
            request,
            username=email,   # email == username
            password=password
        )

        if user is None:
            messages.error(request, "Invalid email or password.")
            return render(request, "accounts/login.html")

        login(request, user)
        return redirect_after_login(user)

    return render(request, "accounts/login.html")


# =====================================================
# 🔁 ROLE-BASED REDIRECT AFTER LOGIN
# =====================================================



def redirect_after_login(user):
    profile = user.profile

    # 🔱 Platform admin
    if user.is_superuser:
        return redirect("/admin/")

    # 🏢 Organization admin → COMPANY DASHBOARD
    if profile.role == Profile.ROLE_ORG_ADMIN:
        return redirect("/accounts/org/dashboard/")

    # 👤 Normal users
    return redirect(settings.LOGIN_REDIRECT_URL)



# =====================================================
# 🚪 LOGOUT
# =====================================================

@login_required
def logout_view(request):
    logout(request)
    return redirect(settings.LOGIN_URL)
