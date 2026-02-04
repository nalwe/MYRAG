from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User

from accounts.models import EmailOTP


# =====================================================
# 🔐 LOGIN STEP 1 — EMAIL + PASSWORD
# =====================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

from accounts.models import EmailOTP


# =====================================================
# 🔐 LOGIN STEP 1 — EMAIL + PASSWORD + SEND OTP
# =====================================================

def login_view(request):
    """
    Step 1:
    - User enters email + password
    - OTP is generated and emailed
    - User redirected to OTP verification
    """

    # Already logged in
    if request.user.is_authenticated:
        return redirect_after_login(request.user)

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, "accounts/login.html")

        # Authenticate using email as username
        user = authenticate(request, username=email, password=password)

        if not user:
            messages.error(request, "Invalid email or password.")
            return render(request, "accounts/login.html")

        # =========================
        # 🔐 GENERATE OTP
        # =========================
        code = EmailOTP.generate_code()
        EmailOTP.objects.create(user=user, code=code)

        # =========================
        # 📧 SEND OTP EMAIL
        # =========================
        try:
            send_mail(
                subject="Your Login Verification Code",
                message=(
                    f"Hello {user.get_full_name() or user.username},\n\n"
                    f"Your login verification code is:\n\n"
                    f"   {code}\n\n"
                    f"This code expires in 10 minutes.\n\n"
                    f"If you did not request this login, please ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            messages.error(
                request,
                "Unable to send verification email. Please try again later."
            )
            return render(request, "accounts/login.html")

        # Store user temporarily in session
        request.session["otp_user_id"] = user.id

        messages.success(
            request,
            "A verification code has been sent to your email."
        )

        return redirect("verify_otp")

    return render(request, "accounts/login.html")


# =====================================================
# 🔐 LOGIN STEP 2 — VERIFY OTP
# =====================================================

def verify_otp(request):
    """
    Step 2:
    - User enters OTP
    - OTP validated
    - User logged in
    """

    user_id = request.session.get("otp_user_id")

    if not user_id:
        messages.error(request, "Session expired. Please login again.")
        return redirect("login")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        if not code:
            messages.error(request, "Please enter the verification code.")
            return render(request, "accounts/verify_otp.html")

        otp = (
            EmailOTP.objects
            .filter(
                user=user,
                code=code,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp:
            messages.error(request, "Invalid verification code.")
            return render(request, "accounts/verify_otp.html")

        if otp.is_expired():
            messages.error(request, "Verification code expired.")
            return render(request, "accounts/verify_otp.html")

        # ✅ Mark OTP as used
        otp.is_used = True
        otp.save(update_fields=["is_used"])

        # ✅ Log user in (explicit backend required)
        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend"
        )

        # Clear temporary session
        request.session.pop("otp_user_id", None)

        return redirect_after_login(user)

    return render(request, "accounts/verify_otp.html")



# =====================================================
# 🔁 ROLE-BASED REDIRECT AFTER LOGIN
# =====================================================

def redirect_after_login(user):
    """
    Centralized redirect logic after successful login.
    """

    profile = user.profile

    # 🌍 Platform admin
    if profile.is_superuser():
        return redirect("admin_dashboard")

    # 🏢 Organization admin
    if profile.is_org_admin():
        return redirect("organization_dashboard")

    # 💬 Normal users
    return redirect("chat_view")



# =====================================================
# 🚪 LOGOUT
# =====================================================

@login_required
def logout_view(request):
    logout(request)
    return redirect("login")
