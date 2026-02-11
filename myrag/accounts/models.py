from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    logo = models.ImageField(upload_to="org_logos/", blank=True, null=True)

    is_active = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    max_users = models.PositiveIntegerField(default=10)

    api_token_limit = models.PositiveBigIntegerField(default=1_000_000)
    api_tokens_used = models.PositiveBigIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def remaining_tokens(self):
        return max(0, self.api_token_limit - self.api_tokens_used)

    @property
    def user_count(self):
        return self.members.filter(is_active=True).count()


# ============================
# 👤 USER PROFILE
# ============================

class Profile(models.Model):

    ROLE_ORG_ADMIN = "org_admin"
    ROLE_PREMIUM = "premium"
    ROLE_BASIC = "basic"

    ROLE_CHOICES = (
        (ROLE_ORG_ADMIN, "Organisation Admin"),
        (ROLE_PREMIUM, "Premium User"),
        (ROLE_BASIC, "Basic User"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="members"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_BASIC,
        db_index=True
    )

    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)

    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["organization"]),
        ]

    def __str__(self):
        return f"{self.user.email or self.user.username} ({self.role})"


# ============================
# 👥 ORGANIZATION MEMBER (SINGLE SOURCE OF TRUTH)
# ============================




# ============================
# 🧾 AUDIT LOG
# ============================

class AuditLog(models.Model):
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions"
    )

    action = models.CharField(max_length=255)
    target = models.CharField(max_length=255)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.actor} → {self.action} → {self.target}"


# ============================
# ✉️ ORGANIZATION INVITE
# ============================

class OrganizationInvite(models.Model):
    email = models.EmailField()

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invites"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} → {self.organization.name}"
