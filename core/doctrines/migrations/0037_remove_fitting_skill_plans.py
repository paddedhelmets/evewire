# Generated to remove unused skill_plans field from Fitting

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_skillplanentry_unique_skill_level'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fitting',
            name='skill_plans',
        ),
    ]
