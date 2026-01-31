from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

User = get_user_model()


# ============================
# 📁 FOLDER
# ============================

class Folder(models.Model):
    name = models.CharField(max_length=255)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="folders",
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    # 🔓 Public folders (visible to same owner)
    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "parent", "owner")

    def __str__(self):
        return self.full_path

    # =========================
    # 📂 TREE HELPERS
    # =========================

    @property
    def full_path(self):
        parts = [self.name]
        parent = self.parent
        while parent:
            parts.append(parent.name)
            parent = parent.parent
        return " / ".join(reversed(parts))

    def is_descendant_of(self, folder):
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
        if self.parent and self.parent == self:
            raise ValidationError("Folder cannot be its own parent.")

        if self.parent and self.parent.is_descendant_of(self):
            raise ValidationError(
                "Cannot move folder inside its own subfolder."
            )

        if self.parent and self.parent.owner != self.owner:
            raise ValidationError("Folder owner mismatch.")

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

    # =========================
    # OWNERSHIP
    # =========================
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documents",
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

    # PostgreSQL full-text search field
    search_vector = SearchVectorField(
        null=True,
        editable=False,
    )

    # =========================
    # 🔐 ACCESS CONTROL
    # =========================
    is_public = models.BooleanField(default=False)
    uploaded_by_admin = models.BooleanField(default=False)

    # =========================
    # METADATA
    # =========================
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            GinIndex(
                fields=["search_vector"],
                name="document_search_vector_gin",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                check=Q(owner__isnull=False),
                name="document_requires_owner",
            ),
        ]

    # =========================
    # STRING / HELPERS
    # =========================
    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.title or self.file.name.rsplit("/", 1)[-1]

    # =========================
    # VALIDATION
    # =========================
    def clean(self):
        if self.folder and self.folder.owner != self.owner:
            raise ValidationError(
                "Document folder must belong to the same owner."
            )

    # =========================
    # SAVE HOOK
    # =========================
    def save(self, *args, **kwargs):

        if not self.title and self.file:
            self.title = self.file.name.rsplit("/", 1)[-1]

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
        related_name="collaborators",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="document_access",
    )

    can_edit = models.BooleanField(default=False)

    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("document", "user")

    def __str__(self):
        return f"{self.user.email} → {self.document.display_name}"
