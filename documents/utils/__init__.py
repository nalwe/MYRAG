from django.db.models import Q

from documents.models import Document
from accounts.models import OrganizationMember


def get_accessible_documents(user):
    """
    Returns all documents the user is allowed to see:
    - Private documents owned by the user
    - Company documents (if the user belongs to an organization)
    - Public documents
    """
    member = OrganizationMember.objects.filter(user=user).first()

    qs = Document.objects.filter(
        Q(owner=user) |
        Q(is_public=True)
    )

    if member:
        qs = qs | Document.objects.filter(
            organization=member.organization
        )

    return qs.distinct()


from .text_extractor import extract_text_from_file

