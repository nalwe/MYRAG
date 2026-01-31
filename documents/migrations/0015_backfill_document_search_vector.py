from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0014_add_document_search_vector"),
    ]

    operations = [
        migrations.RunSQL(
            """
            UPDATE documents_document
            SET search_vector =
                to_tsvector(
                    'english',
                    coalesce(title, '') || ' ' ||
                    coalesce(extracted_text, '') || ' ' ||
                    coalesce(file::text, '')
                )
            WHERE search_vector IS NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
