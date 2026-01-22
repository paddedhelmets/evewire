# Generated manually for fitting-skillplan relationship

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_merge_20260122_1325'),
    ]

    operations = [
        migrations.AddField(
            model_name='fitting',
            name='skill_plans',
            field=models.ManyToManyField(
                blank=True,
                help_text='Skill plans that train the required skills for this fitting',
                related_name='fittings',
                to='core.skillplan',
            ),
        ),
    ]
