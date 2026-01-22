"""
Management command to populate ItemType with skill data from ESI.

This is a quick fix to get skill names displaying properly.
"""

import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from core.eve.models import ItemType


class Command(BaseCommand):
    help = 'Populate ItemType with skill data from ESI'

    # ESI endpoint for universe types
    ESI_TYPE_URL = f"{settings.ESI_BASE_URL}/universe/types/{{type_id}}/"
    ESI_DATASOURCE = f"?datasource={settings.ESI_DATASOURCE}"

    def add_arguments(self, parser):
        parser.add_argument(
            '--skill-ids',
            type=str,
            help='Comma-separated list of skill IDs to populate (default: all synced skills)',
        )

    def handle(self, *args, **options):
        from core.character.models import CharacterSkill

        # Get skill IDs to populate
        if options['skill_ids']:
            skill_ids = [int(s.strip()) for s in options['skill_ids'].split(',')]
        else:
            # Get all unique skill IDs from synced characters
            skill_ids = CharacterSkill.objects.values_list('skill_id', flat=True).distinct()

        self.stdout.write(f'Populating {len(skill_ids)} skills from ESI...')

        created = 0
        updated = 0
        failed = 0

        for skill_id in skill_ids:
            try:
                # Check if already exists
                existing = ItemType.objects.filter(id=skill_id).first()

                # Fetch from ESI
                url = self.ESI_TYPE_URL.format(type_id=skill_id) + self.ESI_DATASOURCE
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                # Get name and category
                name = data.get('name', f'Skill {skill_id}')

                # Skills are in category 16 (per EVE SDE)
                # But ESI uses different structure - check if published
                published = data.get('published', True)

                if existing:
                    if existing.name != name:
                        existing.name = name
                        existing.save()
                        updated += 1
                else:
                    ItemType.objects.create(
                        id=skill_id,
                        name=name,
                        description=data.get('description', ''),
                        group_id=data.get('group_id'),
                        published=published,
                    )
                    created += 1

                if (created + updated) % 10 == 0:
                    self.stdout.write(f'  Progress: {created + updated} populated...')

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Skill {skill_id}: failed - {e}'))
                failed += 1

        self.stdout.write(self.style.SUCCESS(f'\nDone: {created} created, {updated} updated, {failed} failed'))
