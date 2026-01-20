# Generated manually for SDE data models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_skillplan_is_reference'),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemGroup',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('category_id', models.IntegerField(db_index=True, null=True)),
                ('published', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'item group',
                'verbose_name_plural': 'item groups',
                'ordering': ['name'],
                'db_table': 'core_itemgroup',
            },
        ),
        migrations.CreateModel(
            name='ItemCategory',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('published', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'item category',
                'verbose_name_plural': 'item categories',
                'ordering': ['name'],
                'db_table': 'core_itemcategory',
            },
        ),
        migrations.CreateModel(
            name='AttributeType',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('default_value', models.FloatField(null=True, blank=True)),
                ('published', models.BooleanField(default=True)),
                ('display_name', models.CharField(max_length=255, blank=True)),
                ('icon_id', models.IntegerField(null=True, blank=True)),
                ('data_type', models.IntegerField(null=True, blank=True)),
            ],
            options={
                'verbose_name': 'attribute type',
                'verbose_name_plural': 'attribute types',
                'ordering': ['name'],
                'db_table': 'core_attributetype',
            },
        ),
        migrations.CreateModel(
            name='TypeAttribute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('type_id', models.IntegerField(db_index=True)),
                ('attribute_id', models.IntegerField(db_index=True)),
                ('value_int', models.IntegerField(null=True, blank=True)),
                ('value_float', models.FloatField(null=True, blank=True)),
            ],
            options={
                'verbose_name': 'type attribute',
                'verbose_name_plural': 'type attributes',
                'unique_together': {('type_id', 'attribute_id')},
                'ordering': ['type_id', 'attribute_id'],
                'db_table': 'core_typeattribute',
            },
        ),
    ]
