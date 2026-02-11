from django.db.models import Q
from documents.models import Document
from accounts.models import OrganizationMember


def get_accessible_documents(user):
    """
    What a user can see:
    - Superuser / staff: everything
    - Everyone else:
        • Public documents
        • Documents belonging to their organization
    """

    if user.is_superuser or user.is_staff:
        return Document.objects.all()

    member = (
        OrganizationMember.objects
        .select_related("organization")
        .filter(user=user)
        .first()
    )

    qs = Document.objects.filter(is_public=True)

    if member and member.organization:
        qs = qs | Document.objects.filter(
            organization=member.organization
        )

    return qs.distinct()
