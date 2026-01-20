# Generated manually for Phase 1: Attributes & Implants

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alliance_corporation_faction_itemtype_region_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CharacterAttributes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('intelligence', models.SmallIntegerField(default=20)),
                ('perception', models.SmallIntegerField(default=20)),
                ('charisma', models.SmallIntegerField(default=20)),
                ('willpower', models.SmallIntegerField(default=20)),
                ('memory', models.SmallIntegerField(default=20)),
                ('bonus_remap_available', models.IntegerField(default=0)),
                ('synced_at', models.DateTimeField(auto_now_add=True)),
                ('character', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='attributes', to='core.character')),
            ],
            options={
                'verbose_name': 'character attributes',
                'verbose_name_plural': 'character attributes',
                'db_table': 'core_characterattributes',
            },
        ),
        migrations.CreateModel(
            name='CharacterImplant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_id', models.IntegerField(db_index=True)),
                ('synced_at', models.DateTimeField(auto_now_add=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='implants', to='core.character')),
            ],
            options={
                'verbose_name': 'character implant',
                'verbose_name_plural': 'character implants',
                'db_table': 'core_characterimplant',
                'ordering': ['character', 'type_id'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='characterimplant',
            unique_together={('character', 'type_id')},
        ),
    ]
