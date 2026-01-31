from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_enable_pg_trgm"),
    ]

    operations = [

        # 1️⃣ Enable PostgreSQL extensions (idempotent)
        migrations.RunSQL(
            sql="""
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
            CREATE EXTENSION IF NOT EXISTS unaccent;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # 2️⃣ Backfill search_vector
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
