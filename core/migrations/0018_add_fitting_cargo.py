# Generated manually - Add FittingCargoItem model for cargo hold items

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0017_add_fitting_drones'),
    ]

    operations = [
        migrations.CreateModel(
            name='FittingCargoItem',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('item_type_id', models.IntegerField(
                    db_index=True,
                    help_text='ItemType ID for the cargo item'
                )),
                ('quantity', models.IntegerField(
                    help_text='Quantity of this item'
                )),
                (
                    'fitting',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='cargo_items',
                        to='core.fitting'
                    ),
                ),
            ],
            options={
                'verbose_name': 'fitting cargo item',
                'verbose_name_plural': 'fitting cargo items',
                'db_table': 'core_fittingcargoitem',
                'ordering': ['fitting', 'item_type_id'],
            },
        ),
    ]
