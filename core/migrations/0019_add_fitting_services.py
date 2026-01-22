# Generated manually - Add FittingService model for structure service modules

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0018_add_fitting_cargo'),
    ]

    operations = [
        migrations.CreateModel(
            name='FittingService',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('position', models.IntegerField(
                    help_text='Service slot position (0-indexed)'
                )),
                ('service_type_id', models.IntegerField(
                    db_index=True,
                    help_text='ItemType ID for the service module'
                )),
                (
                    'fitting',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='services',
                        to='core.fitting'
                    ),
                ),
            ],
            options={
                'verbose_name': 'fitting service',
                'verbose_name_plural': 'fitting services',
                'db_table': 'core_fittingservice',
                'ordering': ['fitting', 'position'],
            },
        ),
    ]
