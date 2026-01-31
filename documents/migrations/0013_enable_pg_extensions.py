from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_add_search_vector_gin"),
    ]

    operations = [
        # 1️⃣ Enable required Postgres extension
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql=migrations.RunSQL.noop,
        ),

        # 2️⃣ Backfill search_vector safely
        migrations.RunSQL(
            sql="""
            UPDATE documents_document
            SET search_vector =
                setweight(
                    to_tsvector('english', coalesce(file::text, '')),
                    'A'
                ) ||
                setweight(
                    to_tsvector('english', coalesce(extracted_text, '')),
                    'B'
                );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
