from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone

from accounts.models import Profile
from accounts.utils import sync_user_permissions


# ============================
# 🔒 ENFORCE USERNAME = EMAIL
# ============================

@receiver(pre_save, sender=User)
def enforce_username_equals_email(sender, instance, **kwargs):
    """
    Ensure username is always the normalized email.
    This guarantees email-based login works consistently.
    """
    if instance.email:
        normalized_email = instance.email.strip().lower()
        instance.email = normalized_email

        # Only update username if needed (prevents unnecessary writes)
        if instance.username != normalized_email:
            instance.username = normalized_email


# ============================
# 👤 AUTO CREATE PROFILE
# ============================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create Profile for every new user.
    """
    if created:
        Profile.objects.create(
            user=instance,
            role=Profile.ROLE_BASIC,
        )

        sync_user_permissions(instance)


# ============================
# 🔄 SYNC PERMISSIONS ON ROLE CHANGE
# ============================

@receiver(post_save, sender=Profile)
def sync_permissions_on_role_change(sender, instance, **kwargs):
    """
    When Profile.role changes, update Django permissions.
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
    Profile.objects.filter(user=user).update(
        last_login_at=timezone.now()
    )
