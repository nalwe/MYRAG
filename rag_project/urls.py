from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from accounts.views.otp_views import RoleBasedOTPLoginView


from django.shortcuts import redirect

def home(request):
    if request.user.is_authenticated:
        return redirect("chat_view")
    return redirect("login")

urlpatterns = [
    path("admin/", admin.site.urls),

    # ✅ OTP Login
    path("account/login/", RoleBasedOTPLoginView.as_view(), name="login"),

    # 🏠 Home redirect (FIXES 403 ON /)
    path("", home, name="home"),

    # Apps
    path("accounts/", include("accounts.urls")),
    path("documents/", include("documents.urls")),
    path("chat/", include("rag.urls")),   # 👈 moved chat under /chat/
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



