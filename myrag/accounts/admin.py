from django.contrib import admin
from django.contrib.auth.models import User


class UserAdminOverride(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        if obj.email:
            obj.username = obj.email.lower()
        super().save_model(request, obj, form, change)


admin.site.unregister(User)
admin.site.register(User, UserAdminOverride)
