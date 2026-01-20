# Generated manually for reference plans feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_skillplan_skillplanentry'),
    ]

    operations = [
        migrations.AddField(
            model_name='skillplan',
            name='is_reference',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
