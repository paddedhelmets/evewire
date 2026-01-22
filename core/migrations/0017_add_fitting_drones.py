# Generated manually - Add FittingDrone model for drone/fighter bay

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0016_add_fitting_charges'),
    ]

    operations = [
        migrations.CreateModel(
            name='FittingDrone',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('drone_type_id', models.IntegerField(
                    db_index=True,
                    help_text='ItemType ID for the drone/fighter'
                )),
                (
                    'bay_type',
                    models.CharField(
                        choices=[('drone', 'Drone Bay'), ('fighter', 'Fighter Bay')],
                        default='drone',
                        max_length=10
                    ),
                ),
                ('quantity', models.IntegerField(
                    help_text='Quantity of this drone in bay'
                )),
                (
                    'fitting',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='drones',
                        to='core.fitting'
                    ),
                ),
            ],
            options={
                'verbose_name': 'fitting drone',
                'verbose_name_plural': 'fitting drones',
                'db_table': 'core_fittingdrone',
                'ordering': ['fitting', 'bay_type', 'drone_type_id'],
            },
        ),
        migrations.AddIndex(
            model_name='fittingdrone',
            index=models.Index(fields=['fitting', 'bay_type'], name='core_fittingdrone_fitting_bay_idx'),
        ),
    ]
