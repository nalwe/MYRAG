from django.urls import path
from . import views

urlpatterns = [
    path("", views.document_list, name="document_list"),
    path("upload/", views.document_upload, name="document_upload"),
    path("my/", views.my_documents, name="my_documents"),
    path("preview/<int:doc_id>/", views.document_preview, name="document_preview"),
    path("download/<int:doc_id>/", views.document_download, name="document_download"),
    path("<int:doc_id>/delete/", views.delete_document, name="delete_document"),
    path("folders/create/", views.create_folder, name="create_folder"),
    path("move/", views.move_document, name="move_document"),


]
