"""
Management command to populate ItemType from synced data.

Scans all synced character data and fetches missing ItemType entries from ESI.
"""

import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from core.eve.models import ItemType


class Command(BaseCommand):
    help = 'Populate ItemType from synced character data'

    ESI_TYPE_URL = f"{settings.ESI_BASE_URL}/universe/types/{{type_id}}/"
    ESI_DATASOURCE = f"?datasource={settings.ESI_DATASOURCE}"

    def handle(self, *args, **options):
        from core.character.models import (
            CharacterAsset, CharacterSkill, CharacterImplant,
            MarketOrder, IndustryJob, ContractItem
        )

        # Collect all unique type_ids from synced data
        type_ids = set()

        # Skills
        type_ids.update(CharacterSkill.objects.values_list('skill_id', flat=True))

        # Assets
        type_ids.update(CharacterAsset.objects.values_list('type_id', flat=True))

        # Implants
        type_ids.update(CharacterImplant.objects.values_list('type_id', flat=True))

        # Market orders
        type_ids.update(MarketOrder.objects.values_list('type_id', flat=True))

        # Industry jobs (blueprint_type_id and product_type_id)
        type_ids.update(IndustryJob.objects.values_list('blueprint_type_id', flat=True))
        type_ids.update(IndustryJob.objects.values_list('product_type_id', flat=True))

        # Contract items
        type_ids.update(ContractItem.objects.values_list('type_id', flat=True))

        # Filter out existing ItemTypes
        existing_ids = set(ItemType.objects.values_list('id', flat=True))
        missing_ids = type_ids - existing_ids

        self.stdout.write(f'Found {len(type_ids)} unique type_ids, {len(missing_ids)} missing from ItemType')

        if not missing_ids:
            self.stdout.write(self.style.SUCCESS('All ItemTypes already populated'))
            return

        # Sort for consistent fetching
        missing_ids = sorted(missing_ids)

        created = 0
        failed = 0

        for type_id in missing_ids:
            try:
                # Fetch from ESI
                url = self.ESI_TYPE_URL.format(type_id=type_id) + self.ESI_DATASOURCE
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                ItemType.objects.create(
                    id=type_id,
                    name=data.get('name', f'Type {type_id}'),
                    description=data.get('description', ''),
                    group_id=data.get('group_id'),
                    published=data.get('published', True),
                )
                created += 1

                if created % 50 == 0:
                    self.stdout.write(f'  Progress: {created}/{len(missing_ids)} populated...')

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Type {type_id}: failed - {e}'))
                failed += 1

        self.stdout.write(self.style.SUCCESS(f'\nDone: {created} created, {failed} failed'))
