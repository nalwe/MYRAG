from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages

from accounts.models import EmailOTP


def email_login_request(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")
            return redirect("email_login")

        otp = EmailOTP.objects.create(
            user=user,
            code=EmailOTP.generate_code()
        )

        send_mail(
            subject="Your Login Code",
            message=f"Your login code is {otp.code}. It expires in 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        request.session["email_otp_user"] = user.id
        messages.success(request, "OTP sent to your email.")
        return redirect("email_otp_verify")

    return render(request, "accounts/email_login.html")


def email_otp_verify(request):
    user_id = request.session.get("email_otp_user")

    if not user_id:
        return redirect("email_login")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        otp = EmailOTP.objects.filter(
            user_id=user_id,
            code=code,
            is_used=False
        ).last()

        if not otp or otp.is_expired():
            messages.error(request, "Invalid or expired OTP.")
            return redirect("email_otp_verify")

        otp.is_used = True
        otp.save()

        user = otp.user
        login(request, user)

        # 🔐 ROLE-BASED REDIRECT
        if user.is_staff or user.is_superuser:
            return redirect("document_list")

        return redirect("chat")

    return render(request, "accounts/email_otp_verify.html")
