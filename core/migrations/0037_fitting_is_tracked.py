# Generated for is_tracked field on Fitting model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_remove_fitting_skill_plans'),
    ]

    operations = [
        migrations.AddField(
            model_name='fitting',
            name='is_tracked',
            field=models.BooleanField(default=False, db_index=True, help_text='Whether this fitting is tracked for fleet readiness'),
        ),
    ]
