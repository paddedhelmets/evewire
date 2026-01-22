# Generated manually - Add FittingCharge model for module charges/ammo

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0015_alter_character_last_sync_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='FittingCharge',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('charge_type_id', models.IntegerField(
                    db_index=True,
                    help_text='ItemType ID for the charge'
                )),
                ('quantity', models.IntegerField(
                    default=1,
                    help_text='Quantity of charges (for cargo/bay)'
                )),
                (
                    'fitting',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='charges',
                        to='core.fitting'
                    ),
                ),
                (
                    'fitting_entry',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='charges',
                        to='core.fittingentry'
                    ),
                ),
            ],
            options={
                'verbose_name': 'fitting charge',
                'verbose_name_plural': 'fitting charges',
                'db_table': 'core_fittingcharge',
                'ordering': ['fitting', 'fitting_entry'],
            },
        ),
        migrations.AddIndex(
            model_name='fittingcharge',
            index=models.Index(fields=['fitting', 'fitting_entry'], name='core_fitting_fitting_entry_idx'),
        ),
    ]
