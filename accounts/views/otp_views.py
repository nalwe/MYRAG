from two_factor.views import LoginView
from django.urls import reverse

class RoleBasedOTPLoginView(LoginView):
    def get_success_url(self):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return reverse("document_list")

        return reverse("chat_view")
