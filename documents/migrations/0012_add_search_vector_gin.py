from django.db import migrations
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0011_documentaccess_and_more"),
    ]

    operations = [
        GinIndex(
            name="document_title_trgm_gin",
            fields=["title"],
            opclasses=["gin_trgm_ops"],
        ),
        GinIndex(
            name="document_extracted_text_trgm_gin",
            fields=["extracted_text"],
            opclasses=["gin_trgm_ops"],
        ),
    ]
