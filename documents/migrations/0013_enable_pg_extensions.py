from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_add_search_vector_gin"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
    ]
