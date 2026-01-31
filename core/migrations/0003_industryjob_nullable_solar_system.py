# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_mining_ledger'),
    ]

    operations = [
        migrations.AlterField(
            model_name='industryjob',
            name='solar_system_id',
            field=models.IntegerField(db_index=True, null=True, blank=True),
        ),
    ]
