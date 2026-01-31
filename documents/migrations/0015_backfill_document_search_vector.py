from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0014_add_document_search_vector"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            UPDATE documents_document
            SET search_vector =
                setweight(
                    to_tsvector('english', coalesce(title, '')),
                    'A'
                ) ||
                setweight(
                    to_tsvector('english', coalesce(extracted_text, '')),
                    'B'
                )
            WHERE search_vector IS NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
