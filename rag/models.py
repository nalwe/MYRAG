from django.db import models
from django.contrib.auth.models import User
#from django.db import models
from documents.models import Document


# =====================================================
# 💬 CHAT SESSION
# =====================================================

class ChatSession(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_sessions"
    )

    title = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    last_document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.title or f"Chat {self.id}"


# =====================================================
# 📎 CHAT CONTEXT (SELECTED DOCUMENTS)
# =====================================================
class ChatContext(models.Model):
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="contexts"   # 🔑 THIS FIXES YOUR ERROR
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("session", "document")

    def __str__(self):
        return f"Chat {self.session.id} → Doc {self.document.id}"


# =====================================================
# 🗨 CHAT MESSAGE
# =====================================================
class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()

    # 🔍 RAG metadata (sources, citations)
    sources = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} message in chat {self.session.id}"
    



class Embedding(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="embeddings"
    )
    chunk_text = models.TextField()
    embedding = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Embedding(doc={self.document_id})"

