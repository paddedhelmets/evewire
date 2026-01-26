"""
Import EVE fittings from markdown format files.

Usage:
    # Import a single markdown file
    python manage.py import_markdown_fittings path/to/fit.md

    # Import all markdown files from a directory
    python manage.py import_markdown_fittings path/to/directory/

    # Dry run (parse without importing)
    python manage.py import_markdown_fittings path/to/directory/ --dry-run

    # Skip existing fittings (don't update if already exists)
    python manage.py import_markdown_fittings path/to/directory/ --skip-existing

    # Update existing fittings
    python manage.py import_markdown_fittings path/to/directory/ --update

    # Show verbose output
    python manage.py import_markdown_fittings path/to/directory/ --verbose
"""

import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Import EVE fittings from markdown format files'

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            type=str,
            help='Path to markdown file or directory containing .md files',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse files without importing (useful for validation)',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip fittings that already exist (based on ship_type_id + cluster_id)',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing fittings instead of skipping them',
        )
        parser.add_argument(
            '--pattern',
            type=str,
            default='*.md',
            help='File pattern to match (default: *.md)',
        )
        parser.add_argument(
            '--recursive',
            action='store_true',
            help='Search for files recursively in subdirectories',
        )

    def handle(self, *args, **options):
        from core.fitting_formats import FittingImporter, FormatDetectionError
        from core.fitting_formats.exceptions import FittingFormatError
        from core.doctrines.models import Fitting

        path = options['path']
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']
        update = options['update']
        pattern = options['pattern']
        recursive = options['recursive']

        # Check if path exists
        if not os.path.exists(path):
            raise CommandError(f"Path not found: {path}")

        # Collect markdown files
        md_files = []
        path_obj = Path(path)

        if path_obj.is_file():
            if not path_obj.suffix == '.md':
                raise CommandError(f"File must have .md extension: {path}")
            md_files.append(path_obj)
        elif path_obj.is_dir():
            if recursive:
                md_files = list(path_obj.rglob(pattern))
            else:
                md_files = list(path_obj.glob(pattern))

            # Filter to only .md files
            md_files = [f for f in md_files if f.suffix == '.md']
        else:
            raise CommandError(f"Path is neither a file nor a directory: {path}")

        if not md_files:
            self.stdout.write(self.style.WARNING(f"No .md files found in: {path}"))
            return

        # Sort files for consistent ordering
        md_files.sort()

        self.stdout.write(self.style.SUCCESS(f"Found {len(md_files)} markdown file(s) to process"))

        # Import fittings
        imported = []
        updated = []
        skipped = []
        errors = []

        for i, md_file in enumerate(md_files, 1):
            self.stdout.write(f"\n[{i}/{len(md_files)}] Processing: {md_file.name}")

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    self.stdout.write(self.style.WARNING("  - Skipping empty file"))
                    continue

                # Parse fitting
                fitting_data = self._parse_markdown(content)

                # Check if fitting already exists
                cluster_id = fitting_data.metadata.get('cluster_id')
                existing = Fitting.objects.filter(
                    ship_type_id=fitting_data.ship_type_id,
                    cluster_id=cluster_id
                ).first()

                if existing:
                    if skip_existing:
                        skipped.append((md_file.name, existing))
                        self.stdout.write(f"  - Skipping existing: {existing.name}")
                        continue
                    elif update:
                        if dry_run:
                            updated.append((md_file.name, existing))
                            self.stdout.write(f"  - Would update: {existing.name}")
                            continue
                        else:
                            # Update existing fitting
                            self._update_fitting(existing, fitting_data)
                            updated.append((md_file.name, existing))
                            self.stdout.write(self.style.SUCCESS(f"  - Updated: {existing.name}"))
                            continue
                    else:
                        errors.append((md_file.name, f"Fitting already exists: {existing.name}"))
                        self.stdout.write(self.style.ERROR(f"  - Already exists: {existing.name} (use --skip-existing or --update)"))
                        continue

                if dry_run:
                    # Create a mock fitting for display
                    mock_fitting = type('obj', (object,), {
                        'ship_type_name': fitting_data.ship_type_name or f"Type {fitting_data.ship_type_id}",
                        'name': fitting_data.name,
                        'cluster_id': fitting_data.metadata.get('cluster_id'),
                        'fit_count': fitting_data.metadata.get('fit_count'),
                    })()
                    imported.append((md_file.name, mock_fitting))
                    self.stdout.write(f"  - Would import: {mock_fitting.name}")
                else:
                    # Import fitting
                    fitting = FittingImporter.import_from_string(content, format_name='md')
                    imported.append((md_file.name, fitting))
                    self.stdout.write(self.style.SUCCESS(f"  - Imported: {fitting.name}"))

            except FormatDetectionError as e:
                errors.append((md_file.name, f"Format detection failed: {e}"))
                self.stdout.write(self.style.ERROR(f"  - Format detection failed: {e}"))
            except FittingFormatError as e:
                errors.append((md_file.name, f"Parse error: {e}"))
                self.stdout.write(self.style.ERROR(f"  - Parse error: {e}"))
            except Exception as e:
                errors.append((md_file.name, f"Unexpected error: {e}"))
                self.stdout.write(self.style.ERROR(f"  - Unexpected error: {e}"))

        # Output summary
        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
        self.stdout.write("Import Summary")
        self.stdout.write(self.style.SUCCESS(f"{'=' * 60}"))
        self.stdout.write(f"Files processed: {len(md_files)}")
        self.stdout.write(f"Imported: {len(imported)}")
        self.stdout.write(f"Updated: {len(updated)}")
        self.stdout.write(f"Skipped: {len(skipped)}")
        self.stdout.write(f"Errors: {len(errors)}")
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")

        if imported:
            self.stdout.write(self.style.SUCCESS(f"\nImported ({len(imported)}):"))
            for filename, fitting in imported:
                cluster_info = f" (Cluster {fitting.cluster_id})" if fitting.cluster_id else ""
                fit_count = f" - {fitting.fit_count} fits" if hasattr(fitting, 'fit_count') and fitting.fit_count else ""
                self.stdout.write(f"  - {filename}: {fitting.name}{cluster_info}{fit_count}")

        if updated:
            self.stdout.write(self.style.SUCCESS(f"\nUpdated ({len(updated)}):"))
            for filename, fitting in updated:
                self.stdout.write(f"  - {filename}: {fitting.name}")

        if skipped:
            self.stdout.write(self.style.WARNING(f"\nSkipped ({len(skipped)}):"))
            for filename, fitting in skipped[:10]:  # Show first 10
                self.stdout.write(f"  - {filename}: {fitting.name}")
            if len(skipped) > 10:
                self.stdout.write(f"  ... and {len(skipped) - 10} more")

        if errors:
            self.stdout.write(self.style.ERROR(f"\nErrors ({len(errors)}):"))
            for filename, error in errors[:10]:  # Show first 10
                self.stdout.write(f"  - {filename}: {error}")
            if len(errors) > 10:
                self.stdout.write(f"  ... and {len(errors) - 10} more")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a DRY RUN. No fittings were saved to the database."))
            self.stdout.write(self.style.WARNING("Remove --dry-run to perform the actual import."))

    def _parse_markdown(self, content):
        """Parse markdown content and return fitting data."""
        from core.fitting_formats.markdown import MarkdownParser

        parser = MarkdownParser()
        return parser.parse(content)

    def _update_fitting(self, fitting, fitting_data):
        """Update an existing fitting with new data."""
        from core.doctrines.models import (
            FittingEntry,
            FittingCharge,
            FittingDrone,
            FittingCargoItem,
            FittingService,
        )

        with transaction.atomic():
            # Update basic fields
            fitting.name = fitting_data.name
            fitting.description = fitting_data.description
            fitting.fit_count = fitting_data.metadata.get('fit_count')
            fitting.save(update_fields=['name', 'description', 'fit_count'])

            # Clear existing entries
            fitting.entries.all().delete()
            fitting.charges.all().delete()
            fitting.drones.all().delete()
            fitting.cargo_items.all().delete()
            fitting.services.all().delete()

            # Create new entries
            slot_map = {
                'high': fitting_data.high_slots,
                'med': fitting_data.med_slots,
                'low': fitting_data.low_slots,
                'rig': fitting_data.rig_slots,
                'subsystem': fitting_data.subsystem_slots,
            }

            position_map = {}

            for slot_type, modules in slot_map.items():
                for position, type_id in enumerate(modules):
                    if type_id:
                        is_offline = position in fitting_data.offline

                        entry = FittingEntry.objects.create(
                            fitting=fitting,
                            slot_type=slot_type,
                            position=position,
                            module_type_id=type_id,
                            is_offline=is_offline,
                        )

                        global_pos = len(position_map)
                        position_map[global_pos] = entry

                        if global_pos in fitting_data.charges:
                            FittingCharge.objects.create(
                                fitting=fitting,
                                fitting_entry=entry,
                                charge_type_id=fitting_data.charges[global_pos],
                                quantity=1,
                            )

            # Create drones
            for drone_type_id, quantity in fitting_data.drones:
                FittingDrone.objects.create(
                    fitting=fitting,
                    drone_type_id=drone_type_id,
                    bay_type='drone',
                    quantity=quantity,
                )

            # Create cargo items
            for item_type_id, quantity in fitting_data.cargo:
                FittingCargoItem.objects.create(
                    fitting=fitting,
                    item_type_id=item_type_id,
                    quantity=quantity,
                )

            # Create services
            for position, service_type_id in enumerate(fitting_data.services):
                FittingService.objects.create(
                    fitting=fitting,
                    service_type_id=service_type_id,
                    position=position,
                )
