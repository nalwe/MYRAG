from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone

from django_otp.plugins.otp_email.models import EmailDevice

from .models import Profile


# ============================
# 👤 AUTO CREATE PROFILE
# ============================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create Profile for every new user.
    Also sync Django superusers into platform superusers.
    """
    if created:
        role = Profile.ROLE_BASIC

        # If Django superuser → platform superuser
        if instance.is_superuser:
            role = Profile.ROLE_SUPERUSER

        Profile.objects.create(
            user=instance,
            role=role
        )


# ============================
# 🔄 SYNC ROLE IF SUPERUSER CHANGES
# ============================

@receiver(post_save, sender=User)
def sync_superuser_role(sender, instance, **kwargs):
    """
    If a user is promoted/demoted to Django superuser,
    keep Profile.role in sync.
    """
    try:
        profile = instance.profile
    except Profile.DoesNotExist:
        return

    if instance.is_superuser and profile.role != Profile.ROLE_SUPERUSER:
        profile.role = Profile.ROLE_SUPERUSER
        profile.save(update_fields=["role"])

    if not instance.is_superuser and profile.role == Profile.ROLE_SUPERUSER:
        profile.role = Profile.ROLE_BASIC
        profile.save(update_fields=["role"])


# ============================
# 🔐 ENSURE EMAIL OTP DEVICE
# ============================

@receiver(user_logged_in)
def ensure_email_device(sender, user, request, **kwargs):
    """
    Ensure OTP email device exists for the user.
    """
    if not user.email:
        return

    EmailDevice.objects.get_or_create(
        user=user,
        name="default",
        defaults={"email": user.email},
    )

    # Update last login timestamp
    try:
        profile = user.profile
        profile.last_login_at = timezone.now()
        profile.save(update_fields=["last_login_at"])
    except Profile.DoesNotExist:
        pass
