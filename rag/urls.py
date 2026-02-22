from django.urls import path
from .views import chat_view, delete_chat, export_answer_pdf, export_answer_docx
from rag.views import chat_view, delete_chat, start_chat_with_context, export_chat_pdf, export_chat_docx, export_selected_messages_pdf, clear_all_chats

urlpatterns = [
    path("", chat_view, name="chat_view"),
    path("<int:session_id>/", chat_view, name="chat_session"),
    path("chat/<int:session_id>/", chat_view, name="chat_view"),
    path("<int:session_id>/delete/", delete_chat, name="delete_chat"),
    path("export/<int:session_id>/", export_chat_pdf, name="export_chat_pdf"),
    path("start/", start_chat_with_context, name="start_chat_with_context"),
    path("clear-all/", clear_all_chats, name="clear_all_chats"),
    path("export/answer/<int:message_id>/pdf/", export_answer_pdf, name="export_answer_pdf"),
    path("export/answer/<int:message_id>/docx/", export_answer_docx, name="export_answer_docx"),





    #export
    path("export/<int:session_id>/pdf/", export_chat_pdf, name="export_chat_pdf"),
    path("export/<int:session_id>/docx/", export_chat_docx, name="export_chat_docx"),
    path(
        "export/<int:session_id>/selected/",
        export_selected_messages_pdf,
        name="export_selected_messages_pdf",
    ),

]
