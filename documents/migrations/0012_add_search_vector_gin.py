from django.db import migrations
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0011_documentaccess_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="document",
            index=GinIndex(
                fields=["search_vector"],
                name="document_search_vector_gin",
            ),
        ),
    ]
