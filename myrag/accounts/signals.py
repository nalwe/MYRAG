from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone

from .models import Profile
from .utils import sync_user_permissions


# ============================
# 👤 AUTO CREATE PROFILE
# ============================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create Profile for every new user.
    Superusers are handled by Django itself.
    """
    if created:
        profile = Profile.objects.create(
            user=instance,
            role=Profile.ROLE_BASIC,
        )

        # Sync permissions immediately
        sync_user_permissions(instance)


# ============================
# 🔄 SYNC PERMISSIONS ON USER SAVE
# ============================

@receiver(post_save, sender=User)
def sync_permissions_on_user_save(sender, instance, **kwargs):
    """
    Ensure permissions stay correct when user flags change
    (especially is_superuser).
    """
    sync_user_permissions(instance)


# ============================
# 🔄 SYNC PERMISSIONS ON ROLE CHANGE
# ============================

@receiver(post_save, sender=Profile)
def sync_permissions_on_role_change(sender, instance, **kwargs):
    """
    When Profile.role changes (upgrade/downgrade),
    update Django permissions immediately.
    """
    sync_user_permissions(instance.user)


# ============================
# 🕒 UPDATE LAST LOGIN TIMESTAMP
# ============================

@receiver(user_logged_in)
def update_last_login_timestamp(sender, user, request, **kwargs):
    """
    Update Profile.last_login_at whenever user logs in.
    """
    try:
        profile = user.profile
        profile.last_login_at = timezone.now()
        profile.save(update_fields=["last_login_at"])
    except Profile.DoesNotExist:
        pass


# ============================
# 🔐 CLEAR FORCE PASSWORD CHANGE FLAG
# ============================

@receiver(post_save, sender=User)
def clear_force_password_flag(sender, instance, **kwargs):
    """
    When a user's password is changed, clear must_change_password flag.
    """
    try:
        profile = instance.profile
    except Profile.DoesNotExist:
        return

    if profile.must_change_password:
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password"])
