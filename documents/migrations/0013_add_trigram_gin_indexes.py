from django.db import migrations
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_enable_pg_trgm"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="document",
            index=GinIndex(
                name="document_title_trgm_gin",
                fields=["title"],
                opclasses=["gin_trgm_ops"],
            ),
        ),
        migrations.AddIndex(
            model_name="document",
            index=GinIndex(
                name="document_extracted_text_trgm_gin",
                fields=["extracted_text"],
                opclasses=["gin_trgm_ops"],
            ),
        ),
    ]
