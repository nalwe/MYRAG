# accounts/decorators.py
from django.http import HttpResponseForbidden
from .utils import get_user_role

def requires_role(allowed_roles):
    def _decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Not allowed")
        return _wrapped_view
    return _decorator
