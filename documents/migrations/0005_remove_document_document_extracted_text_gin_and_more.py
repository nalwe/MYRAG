# Fixed for PostgreSQL + Django 4.2
# Removes broken GIN index logic that referenced non-existent columns

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_alter_document_options_alter_document_is_public_and_more'),
    ]

    operations = [
        # Safely drop the broken index if it exists
        migrations.RunSQL(
            sql="""
                DROP INDEX IF EXISTS document_extracted_text_gin;
            """,
            reverse_sql="""
                -- no reverse
            """
        ),
    ]
