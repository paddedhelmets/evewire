# Generated manually for fitting-skillplan relationship

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_remove_attributetype_data_type_and_more'),
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
