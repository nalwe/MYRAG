from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField

from accounts.models import Organization


# ============================
# 📁 FOLDER
# ============================

class Folder(models.Model):
    name = models.CharField(max_length=255)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="folders"
    )

    # Organization scope (NULL = personal folder)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="folders",
        null=True,
        blank=True,
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    # 🔓 Public folders (visible inside same organization)
    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

        # Prevent duplicate folder names in same tree + org + owner
        unique_together = ("name", "parent", "owner", "organization")

    def __str__(self):
        return self.full_path

    # =========================
    # 📂 TREE HELPERS
    # =========================

    @property
    def full_path(self):
        """
        Folder path like:
        Root / Sub / Child
        """
        parts = [self.name]
        parent = self.parent
        while parent:
            parts.append(parent.name)
            parent = parent.parent
        return " / ".join(reversed(parts))

    def is_descendant_of(self, folder):
        """
        Prevent circular nesting
        """
        parent = self.parent
        while parent:
            if parent == folder:
                return True
            parent = parent.parent
        return False

    # =========================
    # 🔐 VALIDATION
    # =========================

    def clean(self):

        # Prevent folder being its own parent
        if self.parent and self.parent == self:
            raise ValidationError("Folder cannot be its own parent.")

        # Prevent circular nesting
        if self.parent and self.parent.is_descendant_of(self):
            raise ValidationError(
                "Cannot move folder inside its own subfolder."
            )

        # Prevent mixing organizations
        if self.parent and self.parent.organization != self.organization:
            raise ValidationError(
                "Folder cannot belong to a different organization."
            )

        # Prevent mixing owners
        if self.parent and self.parent.owner != self.owner:
            raise ValidationError(
                "Folder owner mismatch."
            )

    # =========================
    # 📊 HELPERS
    # =========================

    @property
    def document_count(self):
        return self.documents.count()

    @property
    def total_document_count(self):
        count = self.documents.count()
        for child in self.children.all():
            count += child.total_document_count
        return count


# ============================
# 📄 DOCUMENT
# ============================

class Document(models.Model):

    # Personal owner (nullable for org docs)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )

    # Organization owner (nullable for personal docs)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )

    folder = models.ForeignKey(
        Folder,
        related_name="documents",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # =========================
    # FILE
    # =========================
    file = models.FileField(upload_to="documents/")
    file_size = models.BigIntegerField(default=0)
    title = models.CharField(max_length=255, blank=True)

    # =========================
    # 🔑 RAG CORE
    # =========================
    extracted_text = models.TextField(blank=True)
    search_vector = SearchVectorField(null=True)

    # =========================
    # 🔐 ACCESS CONTROL
    # =========================

    # Visible to all users inside same organization
    is_public = models.BooleanField(default=False)

    # Uploaded by org admin or platform admin
    uploaded_by_admin = models.BooleanField(default=False)

    # =========================
    # METADATA
    # =========================
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            GinIndex(fields=["search_vector"]),
        ]

        # 🚨 Ownership safety
        constraints = [
            models.CheckConstraint(
                condition=(
                    # Personal document
                    (
                        models.Q(owner__isnull=False) &
                        models.Q(organization__isnull=True)
                    )
                    |
                    # Organization document
                    (
                        models.Q(owner__isnull=True) &
                        models.Q(organization__isnull=False)
                    )
                    |
                    # Global system document (superuser)
                    (
                        models.Q(owner__isnull=True) &
                        models.Q(organization__isnull=True)
                    )
                ),
                name="document_valid_ownership_scope",
            ),
        ]


    def __str__(self):
        return self.display_name

    # =========================
    # HELPERS
    # =========================

    @property
    def display_name(self):
        return self.title or self.file.name.split("/")[-1]

    def clean(self):
        """
        Prevent folder mismatch between organization and document
        """
        if self.folder:
            if self.folder.organization != self.organization:
                raise ValidationError(
                    "Document folder must belong to the same organization."
                )

    def save(self, *args, **kwargs):

        # Auto-set title
        if not self.title and self.file:
            self.title = self.file.name.split("/")[-1]

        # Auto-set file size
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except Exception:
                pass

        super().save(*args, **kwargs)


# ============================
# 🤝 DOCUMENT COLLABORATION
# ============================

class DocumentAccess(models.Model):

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="collaborators"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="document_access"
    )

    can_edit = models.BooleanField(default=False)

    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("document", "user")

    def __str__(self):
        return f"{self.user.email} → {self.document.display_name}"
