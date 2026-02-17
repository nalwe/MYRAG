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

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="folders",
        db_index=True,
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

    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "parent", "uploaded_by", "organization")

    def __str__(self):
        return self.full_path

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

    def clean(self):
        if self.parent == self:
            raise ValidationError("Folder cannot be its own parent.")

        if self.parent and self.parent.is_descendant_of(self):
            raise ValidationError("Cannot nest folder inside itself.")

        if self.parent and self.parent.organization != self.organization:
            raise ValidationError("Folder organization mismatch.")

        if self.parent and self.parent.uploaded_by != self.uploaded_by:
            raise ValidationError("Folder uploaded_by mismatch.")

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

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents",
        db_index=True,
    )

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

    file = models.FileField(upload_to="documents/")
    file_size = models.BigIntegerField(default=0)
    title = models.CharField(max_length=255, blank=True)

    extracted_text = models.TextField(blank=True)
    search_vector = SearchVectorField(null=True)

    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            GinIndex(fields=["search_vector"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_public=True, organization__isnull=True)
                    | models.Q(is_public=False)
                ),
                name="public_docs_have_no_org",
            ),
        ]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.title or self.file.name.split("/")[-1]

    def clean(self):
        if self.folder and self.folder.organization != self.organization:
            raise ValidationError(
                "Document folder must belong to the same organization."
            )

        if self.is_public and self.organization is not None:
            raise ValidationError(
                "Public documents cannot belong to an organization."
            )

    def save(self, *args, **kwargs):
        if not self.title and self.file:
            self.title = self.file.name.split("/")[-1]

        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except Exception:
                pass

        # Enforce validation always
        self.full_clean()
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
        db_index=True,
    )

    can_edit = models.BooleanField(default=False)

    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("document", "user")

    def __str__(self):
        return f"{self.user.email} → {self.document.display_name}"
