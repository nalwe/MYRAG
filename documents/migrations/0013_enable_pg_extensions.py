from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_enable_pg_trgm"),
    ]

    operations = [
        # Enable PostgreSQL extensions ONLY
        migrations.RunSQL(
            sql="""
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
            CREATE EXTENSION IF NOT EXISTS unaccent;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
