from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0009_document_documents_d_search__05a045_gin"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="document",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(organization__isnull=True, owner__isnull=False)
                    | models.Q(organization__isnull=False, owner__isnull=True)
                    | models.Q(organization__isnull=True, owner__isnull=True)
                ),
                name="document_single_owner_or_org",
            ),
        ),
    ]
