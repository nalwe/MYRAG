from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0009_document_documents_d_search__05a045_gin"),
    ]

    operations = [
        # NOTE:
        # Ownership validation (owner vs organization) is enforced
        # at the model level via Document.clean().
        #
        # Django 4.2 does NOT support CheckConstraint conditions
        # involving ForeignKey joins, so we intentionally avoid
        # a database-level constraint here.
    ]
