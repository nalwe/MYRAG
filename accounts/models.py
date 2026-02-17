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

from django.db import models
from django.contrib.auth.models import User

#from organizations.models import Organization


class Profile(models.Model):

    # ==========================
    # Role definitions
    # ==========================
    ROLE_ORG_ADMIN = "org_admin"
    ROLE_PREMIUM = "premium"
    ROLE_BASIC = "basic"

    ROLE_CHOICES = (
        (ROLE_ORG_ADMIN, "Organisation Admin"),
        (ROLE_PREMIUM, "Premium User"),
        (ROLE_BASIC, "Basic User"),
    )

    # ==========================
    # Core relations
    # ==========================
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

    # ==========================
    # Role & status
    # ==========================
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_BASIC,
        db_index=True
    )

    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)

    # ==========================
    # Tracking
    # ==========================
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ==========================
    # Convenience properties
    # ==========================
    @property
    def is_org_admin(self):
        return self.role == self.ROLE_ORG_ADMIN

    @property
    def is_premium(self):
        return self.role == self.ROLE_PREMIUM

    @property
    def is_basic(self):
        return self.role == self.ROLE_BASIC

    # ==========================
    # Meta
    # ==========================
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

class OrganizationMember(models.Model):

    ROLE_OWNER = "uploaded_by"
    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"

    ROLE_CHOICES = (
        (ROLE_OWNER, "uploaded_by"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_MEMBER, "Member"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="organization_memberships"
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="organization_members"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_MEMBER
    )

    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "organization")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["organization"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.organization.name} ({self.role})"

    def is_uploaded_by(self):
        return self.role == self.ROLE_OWNER

    def is_admin(self):
        return self.role in (self.ROLE_OWNER, self.ROLE_ADMIN)

    def can_manage_users(self):
        return self.is_admin()

    def is_suspended(self):
        return not self.is_active or not self.organization.is_active


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
