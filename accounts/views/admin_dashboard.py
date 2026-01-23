from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from accounts.models import AuditLog
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User



@staff_member_required
def admin_dashboard(request):
    return render(request, "admin/dashboard.html")


from django.core.paginator import Paginator


@login_required
@user_passes_test(lambda u: u.is_superuser)
def audit_log(request):
    logs_qs = AuditLog.objects.select_related(
        "actor"
    ).order_by("-created_at")

    paginator = Paginator(logs_qs, 50)  # 50 per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "accounts/audit_log.html", {
        "page_obj": page_obj,
    })





@login_required
@require_POST
def change_user_role(request, user_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    user = get_object_or_404(User, id=user_id)

    # Prevent self-edit
    if user.id == request.user.id:
        return JsonResponse({"error": "You cannot change your own role"}, status=400)

    new_role = request.POST.get("role")
    if new_role not in ["admin", "premium", "basic"]:
        return JsonResponse({"error": "Invalid role"}, status=400)

    profile = user.profile
    profile.role = new_role
    profile.save()

    # Sync staff flag
    user.is_staff = (new_role == "admin")
    user.save()

    return JsonResponse({
        "success": True,
        "user_id": user.id,
        "new_role": new_role,
    })
