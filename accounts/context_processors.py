from accounts.models import Profile
from accounts.models import OrganizationMember

def user_profile(request):
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return {"profile": profile}
    return {}




def org_context(request):
    is_org_admin = False

    if request.user.is_authenticated:
        is_org_admin = OrganizationMember.objects.filter(
            user=request.user,
            role="admin"
        ).exists()

    return {
        "is_org_admin": is_org_admin
    }

