# Generated manually - Add is_offline field to FittingEntry

from django.db import migrations, models


def set_offline_default(apps, schema_editor):
    """
    Set is_offline=False for all existing FittingEntry records.
    """
    FittingEntry = apps.get_model('core', 'FittingEntry')

    # Update all records where is_offline is NULL to False
    FittingEntry.objects.filter(is_offline__isnull=True).update(is_offline=False)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0019_add_fitting_services'),
    ]

    operations = [
        # Step 1: Add field as nullable (allows existing rows to have NULL values)
        migrations.AddField(
            model_name='fittingentry',
            name='is_offline',
            field=models.BooleanField(
                blank=True,
                null=True,
                help_text='Whether this module is fitted offline'
            ),
        ),
        # Step 2: RunPython data migration - set all NULL values to False
        migrations.RunPython(
            code=set_offline_default,
            reverse_code=migrations.RunPython.noop,
        ),
        # Step 3: Alter field to be non-nullable with default=False
        migrations.AlterField(
            model_name='fittingentry',
            name='is_offline',
            field=models.BooleanField(
                default=False,
                help_text='Whether this module is fitted offline'
            ),
        ),
    ]
