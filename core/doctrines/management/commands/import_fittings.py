"""
Import EVE fittings from EFT/DNA/XML format files.

Usage:
    python manage.py import_fittings fittings.txt --format eft
    python manage.py import_fittings fittings.txt --format eft --dry-run
    python manage.py import_fittings fittings.txt --format eft --bulk
    python manage.py import_fittings fittings.txt --format eft --owner username
"""

import os
import re
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Import EVE fittings from EFT/DNA/XML format files'

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            type=str,
            help='Path to the fittings file to import',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['eft', 'dna', 'xml'],
            help='Format of the fittings file (default: auto-detect)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse the file without importing (useful for validation)',
        )
        parser.add_argument(
            '--bulk',
            action='store_true',
            help='Import multiple fittings from a single file',
        )
        parser.add_argument(
            '--owner',
            type=str,
            help='Username to assign as owner of imported fittings (for DB tracking)',
        )

    def handle(self, *args, **options):
        from core.fitting_formats import FittingImporter, detect_format, FormatDetectionError
        from core.fitting_formats.exceptions import FittingFormatError

        file_path = options['file']
        format_name = options.get('format', '')
        dry_run = options['dry_run']
        bulk = options['bulk']
        owner_username = options.get('owner', '')

        # Check if file exists
        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            raise CommandError("File encoding error. Please use a UTF-8 encoded file.")

        if not content.strip():
            raise CommandError("File is empty")

        # Get owner user if specified
        owner = None
        if owner_username:
            User = get_user_model()
            try:
                owner = User.objects.get(username=owner_username)
                self.stdout.write(f"Importing for user: {owner_username}")
            except User.DoesNotExist:
                raise CommandError(f"User not found: {owner_username}")

        # Auto-detect format if not specified
        if not format_name:
            try:
                format_name = detect_format(content)
                self.stdout.write(f"Auto-detected format: {format_name}")
            except FormatDetectionError:
                raise CommandError("Could not auto-detect format. Please specify --format")

        # Import fittings
        imported = []
        errors = []

        if bulk and format_name == 'eft':
            # Split EFT file by fitting headers
            pattern = r'\[([^,\]]+),\s*([^\]]+)\]'
            parts = re.split(pattern, content)

            for i in range(1, len(parts), 3):
                if i + 2 >= len(parts):
                    break
                ship_name = parts[i].strip()
                fitting_name = parts[i + 1].strip()
                fitting_content = f'[{ship_name}, {fitting_name}]'

                # Add remaining content until next header or end
                j = i + 2
                while j < len(parts) and not parts[j].startswith('['):
                    fitting_content += parts[j]
                    j += 1

                self._import_single_fitting(
                    fitting_content,
                    format_name,
                    dry_run,
                    imported,
                    errors,
                    owner
                )

        elif bulk and format_name == 'xml':
            # Import multiple fittings from XML
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(content)
                fitting_elems = root.findall('.//fitting')

                if not fitting_elems:
                    # Try direct parsing of single fitting
                    self._import_single_fitting(
                        content,
                        format_name,
                        dry_run,
                        imported,
                        errors,
                        owner
                    )
                else:
                    for fitting_elem in fitting_elems:
                        fitting_xml = ET.tostring(fitting_elem, encoding='unicode')
                        self._import_single_fitting(
                            f'<fittings>{fitting_xml}</fittings>',
                            format_name,
                            dry_run,
                            imported,
                            errors,
                            owner
                        )
            except Exception as e:
                errors.append(f'XML parsing error: {e}')

        else:
            # Single fitting import
            self._import_single_fitting(
                content,
                format_name,
                dry_run,
                imported,
                errors,
                owner
            )

        # Output results
        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 50}"))
        self.stdout.write(f"Import Summary")
        self.stdout.write(self.style.SUCCESS(f"{'=' * 50}"))
        self.stdout.write(f"Format: {format_name}")
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        self.stdout.write(f"Imported: {len(imported)}")
        self.stdout.write(f"Errors: {len(errors)}")

        if imported:
            self.stdout.write(self.style.SUCCESS("\nImported Fittings:"))
            for fitting in imported:
                self.stdout.write(f"  - {fitting.ship_type_name}: {fitting.name}")

        if errors:
            self.stdout.write(self.style.ERROR("\nErrors:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a DRY RUN. No fittings were saved to the database."))
            self.stdout.write(self.style.WARNING("Remove --dry-run to perform the actual import."))

    def _import_single_fitting(self, content, format_name, dry_run, imported, errors, owner=None):
        """Import a single fitting from content."""
        from core.fitting_formats import FittingImporter
        from core.fitting_formats.exceptions import FittingFormatError

        try:
            fitting = FittingImporter.import_from_string(
                content,
                format_name=format_name,
                auto_detect=False,
            )

            if owner and not dry_run:
                # Add owner metadata if needed
                # This assumes Fitting model has an owner field or similar
                # Adjust as needed based on your model
                pass

            imported.append(fitting)

        except FittingFormatError as e:
            errors.append(str(e))
