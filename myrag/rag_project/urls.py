from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


# =========================
# 🏠 HOME ROUTE
# =========================
def home(request):
    if request.user.is_authenticated:
        return redirect("chat_view")
    return redirect("login")


urlpatterns = [

    # Django Admin
    path("admin/", admin.site.urls),

    # Home redirect
    path("", home, name="home"),

    # App Routes
    path("accounts/", include("accounts.urls")),
    path("documents/", include("documents.urls")),
    path("chat/", include("rag.urls")),
]


# =========================
# MEDIA FILES (DEBUG ONLY)
# =========================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
