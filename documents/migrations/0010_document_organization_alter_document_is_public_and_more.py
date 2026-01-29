from django.db import migrations, models



migrations.AddConstraint(
    model_name='document',
    constraint=models.CheckConstraint(
        condition=(
            models.Q(organization__isnull=True, owner__isnull=False) |
            models.Q(organization__isnull=False, owner__isnull=True) |
            models.Q(organization__isnull=True, owner__isnull=True)
        ),
        name='document_single_owner_or_org',
    ),
),
