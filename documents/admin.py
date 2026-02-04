from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("file", "owner", "is_public", "uploaded_by_admin")
    list_filter = ("is_public", "uploaded_by_admin")
    search_fields = ("file",)
