from django.contrib import admin
from documents.models import Document, Folder


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "uploaded_by",
        "created_at",
    )
    search_fields = ("name", "uploaded_by__username")
    list_filter = ("created_at",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "uploaded_by",
        "organization",
        "created_at",
    )
    search_fields = (
        "title",
        "file",
        "uploaded_by__username",
        "organization__name",
    )
    list_filter = (
        "created_at",
        "organization",
    )
