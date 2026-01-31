# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_add_needs_reauth'),
    ]

    operations = [
        migrations.AddField(
            model_name='characterasset',
            name='tree_id',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
