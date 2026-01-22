# Generated manually - Fix invalid last_sync_status values

from django.db import migrations, models

# Valid status values from SyncStatus
VALID_STATUSES = ['pending', 'in_progress', 'success', 'failed', 'rate_limited', 'needs_reauth']


def fix_invalid_sync_status(apps, schema_editor):
    """
    Fix any invalid last_sync_status values in the database.

    This can happen if:
    - Data was created before the needs_reauth choice was added
    - Data was corrupted or manually edited
    - Database constraints weren't properly enforced
    """
    Character = apps.get_model('core', 'Character')

    # Find all characters with invalid status
    invalid_characters = Character.objects.exclude(last_sync_status__in=VALID_STATUSES)

    count = invalid_characters.count()
    if count > 0:
        print(f"Found {count} characters with invalid last_sync_status, fixing...")

        for character in invalid_characters:
            old_status = character.last_sync_status
            # Default to 'pending' for invalid statuses
            character.last_sync_status = 'pending'
            character.save(update_fields=['last_sync_status'])
            print(f"  Character {character.id} ({character.character_name}): {old_status} -> pending")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_add_fitting_entry_offline'),
    ]

    operations = [
        # Run the data migration
        migrations.RunPython(
            code=fix_invalid_sync_status,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
