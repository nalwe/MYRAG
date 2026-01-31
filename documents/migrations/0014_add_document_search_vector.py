from django.db import migrations
from django.contrib.postgres.search import SearchVectorField


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0013_enable_pg_extensions"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="search_vector",
            field=SearchVectorField(null=True),
        ),
    ]
