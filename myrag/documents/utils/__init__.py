from django.db.models import Q

from documents.models import Document
from accounts.models import OrganizationMember
from .text_extractor import extract_text_from_file


def get_accessible_documents(user):
    """
    Returns all documents the user is allowed to see:
    - Documents uploaded by the user
    - Organization documents (if the user belongs to an organization)
    - Public documents
    """

    # Superusers see everything
    if user.is_superuser:
        return Document.objects.all()

    member = OrganizationMember.objects.filter(user=user).first()

    # Base access: own + public
    qs = Document.objects.filter(
        Q(uploaded_by=user) |
        Q(is_public=True)
    )

    # Organization documents
    if member and member.organization:
        qs = qs | Document.objects.filter(
            organization=member.organization
        )

    return qs.distinct()
