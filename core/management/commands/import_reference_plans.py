"""
Management command to import reference skill plans from the plans/ directory.

Imports Imperium (or other) skill plans as reference plans visible to all users.
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Import reference skill plans from plans/ directory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-import plans even if they already exist',
        )

    def handle(self, *args, **options):
        from core.character.models import SkillPlan, SkillPlanEntry
        from core.eve.models import ItemType
        from core.skill_plans import SkillPlanImporter

        # Get plans directory (at evewire root)
        plans_dir = Path(settings.BASE_DIR).parent.parent / 'plans'

        if not plans_dir.exists():
            self.stdout.write(self.style.ERROR(f'Plans directory not found: {plans_dir}'))
            return

        # Find all XML files
        xml_files = list(plans_dir.glob('*.xml'))
        if not xml_files:
            self.stdout.write(self.style.WARNING(f'No XML files found in {plans_dir}'))
            return

        self.stdout.write(f'Found {len(xml_files)} plan files')

        imported = 0
        skipped = 0
        errors = 0

        for xml_file in xml_files:
            # Extract plan name from filename (remove pilot name prefix)
            filename = xml_file.stem
            if ' - ' in filename:
                # Remove pilot name prefix
                plan_name = filename.split(' - ', 1)[1]
            else:
                plan_name = filename

            self.stdout.write(f'\nProcessing: {plan_name}')

            # Check if already exists
            if SkillPlan.objects.filter(name=plan_name, is_reference=True).exists():
                if options['force']:
                    self.stdout.write(self.style.WARNING('  Force re-import: deleting existing plan'))
                    SkillPlan.objects.filter(name=plan_name, is_reference=True).delete()
                else:
                    self.stdout.write(self.style.WARNING('  Skipping: already exists'))
                    skipped += 1
                    continue

            try:
                # Read XML content
                with open(xml_file, 'r') as f:
                    xml_content = f.read()

                # Create plan using importer (without owner for reference plans)
                plan = SkillPlan.objects.create(
                    name=plan_name,
                    description=f'Reference skill plan imported from {filename}',
                    owner=None,
                    is_reference=True,
                    display_order=imported,
                )

                # Parse and add entries
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_content)

                for entry_elem in root.findall('entry'):
                    skill_id = int(entry_elem.get('skillID'))
                    level = int(entry_elem.get('level', 0))

                    if level == 0:
                        continue

                    # Check if skill exists in SDE
                    try:
                        ItemType.objects.get(id=skill_id)
                    except ItemType.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'  Skill {skill_id} not in SDE, skipping'))
                        continue

                    # Check if already in plan (some plans have multiple entries for same skill at different levels)
                    existing = SkillPlanEntry.objects.filter(
                        skill_plan=plan,
                        skill_id=skill_id
                    ).first()

                    if existing:
                        # Update to highest level
                        if level > existing.level:
                            existing.level = level
                            existing.save()
                    else:
                        # Create new entry
                        SkillPlanEntry.objects.create(
                            skill_plan=plan,
                            skill_id=skill_id,
                            level=level,
                            display_order=SkillPlanEntry.objects.filter(skill_plan=plan).count(),
                        )

                skill_count = plan.entries.count()
                if skill_count > 0:
                    self.stdout.write(self.style.SUCCESS(f'  Imported: {skill_count} skills'))
                    imported += 1
                else:
                    self.stdout.write(self.style.WARNING('  No skills imported (SDE not populated), keeping plan as reference'))
                    imported += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error: {e}'))
                errors += 1

        self.stdout.write(f'\nSummary: {imported} imported, {skipped} skipped, {errors} errors')
