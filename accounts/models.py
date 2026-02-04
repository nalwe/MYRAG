from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import random
import uuid
from django.utils import timezone


# ============================
# 🏢 ORGANIZATION
# ============================

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)

    # Branding
    logo = models.ImageField(
        upload_to="org_logos/",
        blank=True,
        null=True
    )

    # System status
    is_active = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    # User limits
    max_users = models.PositiveIntegerField(default=10)

    # API quota
    api_token_limit = models.PositiveBigIntegerField(default=1_000_000)
    api_tokens_used = models.PositiveBigIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        status = "Active" if self.is_active else "Archived"
        return f"{self.name} ({status})"

    # =================================================
    # ✅ RELATION HELPERS (CORRECT RELATED NAME)
    # =================================================

    @property
    def members(self):
        """
        Canonical access to organization members.
        """
        return self.organization_members.all()

    @property
    def active_members(self):
        return self.organization_members.filter(is_active=True)

    # Backward compatibility (old typo references)
    @property
    def organisation_members(self):
        return self.organization_members.all()

    # =================================================
    # 📊 BUSINESS HELPERS
    # =================================================

    @property
    def remaining_tokens(self):
        return max(0, self.api_token_limit - self.api_tokens_used)

    @property
    def is_suspended(self):
        return not self.is_active

    @property
    def user_count(self):
        return self.active_members.count()

    @property
    def tier_label(self):
        count = self.user_count

        if count <= 10:
            return "≤ 10 users"
        elif count <= 20:
            return "≤ 20 users"
        elif count <= 50:
            return "≤ 50 users"
        elif count <= 100:
            return "≤ 100 users"
        elif count <= 200:
            return "≤ 200 users"
        elif count <= 500:
            return "≤ 500 users"
        elif count <= 800:
            return "≤ 800 users"
        else:
            return "1000+ users"



# ============================
# 👤 USER PROFILE
# ============================

class Profile(models.Model):

    ROLE_SUPERUSER = "superuser"
    ROLE_ORG_ADMIN = "org_admin"
    ROLE_PREMIUM = "premium"
    ROLE_BASIC = "basic"

    ROLE_CHOICES = (
        (ROLE_SUPERUSER, "Superuser"),
        (ROLE_ORG_ADMIN, "Organization Admin"),
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
        default=ROLE_BASIC
    )

    is_active = models.BooleanField(default=True)

    last_login_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["organization"]),
        ]

    def __str__(self):
        return f"{self.user.email or self.user.username} ({self.role})"

    # ---------- Role Helpers ----------

    def is_superuser(self):
        return self.role == self.ROLE_SUPERUSER

    def is_org_admin(self):
        return self.role == self.ROLE_ORG_ADMIN

    def can_upload_documents(self):
        return self.role in (self.ROLE_ORG_ADMIN,)

    def can_invite_users(self):
        return self.role in (self.ROLE_ORG_ADMIN,)

    def can_use_ai(self):
        return self.role in (
            self.ROLE_ORG_ADMIN,
            self.ROLE_PREMIUM,
            self.ROLE_BASIC,
        )

    def is_suspended(self):
        if not self.is_active:
            return True

        if self.organization and not self.organization.is_active:
            return True

        return False


# ============================
# 🔐 EMAIL OTP LOGIN
# ============================

class EmailOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    EXPIRY_MINUTES = 10

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(
            minutes=self.EXPIRY_MINUTES
        )

    @staticmethod
    def generate_code():
        return f"{random.randint(100000, 999999)}"

    def __str__(self):
        return f"{self.user} | {self.code}"


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
# 👥 ORGANIZATION MEMBER
# ============================

class OrganizationMember(models.Model):

    ROLE_OWNER = "owner"
    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"

    ROLE_CHOICES = (
        (ROLE_OWNER, "Owner"),
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

    # ---------- Role Helpers ----------

    def is_owner(self):
        return self.role == self.ROLE_OWNER

    def is_admin(self):
        return self.role in (self.ROLE_OWNER, self.ROLE_ADMIN)

    def can_manage_users(self):
        return self.is_admin()

    def is_suspended(self):
        return not self.is_active or not self.organization.is_active
    

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

