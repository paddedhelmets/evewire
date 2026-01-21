# Generated manually - Rename Doctrine to Fitting

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_typeattribute_id_and_more'),
    ]

    operations = [
        # Rename Doctrine -> Fitting
        migrations.RenameModel('Doctrine', 'Fitting'),
        # Rename DoctrineEntry -> FittingEntry
        migrations.RenameModel('DoctrineEntry', 'FittingEntry'),
        # Rename AssetMatch -> FittingMatch
        migrations.RenameModel('AssetMatch', 'FittingMatch'),

        # Rename foreign key fields in FittingEntry
        migrations.RenameField(
            model_name='fittingentry',
            old_name='doctrine',
            new_name='fitting',
        ),

        # Rename foreign key fields in FittingMatch
        migrations.RenameField(
            model_name='fittingmatch',
            old_name='doctrine',
            new_name='fitting',
        ),

        # Rename foreign key fields in ShoppingList
        migrations.RenameField(
            model_name='shoppinglist',
            old_name='doctrine',
            new_name='fitting',
        ),

        # Rename related_name for character in FittingMatch
        migrations.AlterField(
            model_name='fittingmatch',
            name='character',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='fitting_matches',
                to='core.character'
            ),
        ),
    ]
