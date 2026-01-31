# Generated manually for mining ledger feature

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MiningLedgerEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('solar_system_id', models.IntegerField(db_index=True)),
                ('type_id', models.IntegerField(db_index=True)),
                ('quantity', models.IntegerField(default=0)),
                ('synced_at', models.DateTimeField(auto_now_add=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mining_entries', to='core.character')),
            ],
            options={
                'verbose_name': 'mining ledger entry',
                'verbose_name_plural': 'mining ledger entries',
                'db_table': 'core_miningledgerentry',
                'ordering': ['-date', '-quantity'],
                'unique_together': {('character', 'date', 'solar_system_id', 'type_id')},
            },
        ),
    ]
