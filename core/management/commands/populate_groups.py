"""
Management command to populate ItemGroup from ESI.
"""

import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from core.eve.models import ItemGroup


class Command(BaseCommand):
    help = 'Populate ItemGroup from ESI'

    ESI_GROUP_URL = f"{settings.ESI_BASE_URL}/universe/groups/{{group_id}}/"
    ESI_DATASOURCE = f"?datasource={settings.ESI_DATASOURCE}"

    def handle(self, *args, **options):
        from core.character.models import CharacterSkill
        from core.eve.models import ItemType

        # Get all unique group_ids from skills
        skill_ids = CharacterSkill.objects.values_list('skill_id', flat=True).distinct()
        group_ids = set(ItemType.objects.filter(id__in=skill_ids).values_list('group_id', flat=True))

        self.stdout.write(f'Fetching {len(group_ids)} item groups from ESI...')

        created = 0
        updated = 0
        failed = 0

        for group_id in sorted(group_ids):
            try:
                # Check if already exists
                existing = ItemGroup.objects.filter(id=group_id).first()

                # Fetch from ESI
                url = self.ESI_GROUP_URL.format(group_id=group_id) + self.ESI_DATASOURCE
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                if existing:
                    if existing.name != data.get('name', f'Group {group_id}'):
                        existing.name = data.get('name', f'Group {group_id}')
                        existing.category_id = data.get('category_id')
                        existing.save()
                        updated += 1
                else:
                    ItemGroup.objects.create(
                        id=group_id,
                        name=data.get('name', f'Group {group_id}'),
                        category_id=data.get('category_id'),
                        published=data.get('published', True),
                    )
                    created += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Group {group_id}: failed - {e}'))
                failed += 1

        self.stdout.write(self.style.SUCCESS(f'\nDone: {created} created, {updated} updated, {failed} failed'))
