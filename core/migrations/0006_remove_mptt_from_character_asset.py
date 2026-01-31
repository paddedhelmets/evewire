# Generated manually - Remove MPTT from CharacterAsset

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_add_tree_id_to_character_asset'),
    ]

    operations = [
        # Remove MPTT-specific fields
        migrations.RemoveField(
            model_name='characterasset',
            name='level',
        ),
        migrations.RemoveField(
            model_name='characterasset',
            name='lft',
        ),
        migrations.RemoveField(
            model_name='characterasset',
            name='rght',
        ),
        migrations.RemoveField(
            model_name='characterasset',
            name='tree_id',
        ),
        # Convert parent from TreeForeignKey to regular ForeignKey
        migrations.AlterField(
            model_name='characterasset',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='children',
                to='core.characterasset'
            ),
        ),
    ]
