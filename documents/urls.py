from django.urls import path
from . import views
from .views import edit_document, delete_document, document_versions # share_document
from .views import (
    bulk_delete_documents,
    document_inline_update,
    ajax_document_search,
    share_document,
    move_document,
)

urlpatterns = [
    # =========================
    # DOCUMENTS
    # =========================
    path("", views.document_list, name="document_list"),
    path("upload/", views.document_upload, name="document_upload"),
    path("my/", views.my_documents, name="my_documents"), # 👈 premium docs
    path("<int:document_id>/edit/", edit_document, name="edit_document"),
    path("<int:document_id>/delete/", delete_document, name="delete_document"),
    path("<int:document_id>/edit/", edit_document, name="edit_document"),
    path("<int:document_id>/versions/", document_versions, name="document_versions"),
    path("<int:document_id>/share/", share_document, name="share_document"),
    path("move/", move_document, name="move_document"),




    # --- Document preview & actions ---
    # Primary preview URL (used by citations UI)
    path("preview/<int:document_id>/", views.document_preview, name="document_preview"),

    # Backward-compatible preview URL (DO NOT REMOVE)
    path("<int:doc_id>/preview/", views.document_preview, name="document_preview_legacy"),

    path("<int:doc_id>/download/", views.document_download, name="document_download"),
    path("<int:doc_id>/delete/", views.document_delete, name="document_delete"),

    # =========================
    # BULK / INLINE
    # =========================
    path("bulk-delete/", bulk_delete_documents, name="bulk_delete_documents"),
    path("<int:pk>/inline-update/", document_inline_update, name="document_inline_update"),

    # =========================
    # SEARCH
    # =========================
    path("ajax-search/", ajax_document_search, name="ajax_document_search"),

    # =========================
    # FOLDER OPERATIONS
    # =========================
    path("folders/move/", views.move_folder, name="move_folder"),
    path("folders/create/", views.create_folder, name="create_folder"),
    path("folders/<int:folder_id>/delete/", views.delete_folder, name="delete_folder"),
    path("folders/<int:folder_id>/rename/", views.rename_folder, name="rename_folder"),
    

    # =========================
    # ADMIN
    # =========================
    path("toggle-public/<int:doc_id>/", views.toggle_public, name="toggle_public"),
]
