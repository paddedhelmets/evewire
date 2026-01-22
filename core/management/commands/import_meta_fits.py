"""
Import meta fits from career research clustering.

Loads reconciled EFT fits with provenance descriptions and imports them
into evewire for users to access.

Usage:
    python manage.py import_meta_fits --ship 22464 --cluster 2
    python manage.py import_meta_fits --all-ships --min-samples 10
    python manage.py import_meta_fits --import-dir output/reconciled
"""

import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.fitting_formats import FittingImporter
from core.doctrines.models import Fitting


class Command(BaseCommand):
    help = 'Import meta fits from career research clustering with provenance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--import-dir',
            type=str,
            default='output/reconciled',
            help='Directory containing reconciled fit markdown files',
        )
        parser.add_argument(
            '--ship',
            type=int,
            action='append',
            help='Ship typeID to import (can specify multiple)',
        )
        parser.add_argument(
            '--all-ships',
            action='store_true',
            help='Import all ships in the import directory',
        )
        parser.add_argument(
            '--min-samples',
            type=int,
            default=5,
            help='Minimum samples required to import a cluster (default: 5)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse files without importing',
        )

    def handle(self, *args, **options):
        import_dir = Path(options['import_dir'])
        ship_ids = options.get('ship', [])
        all_ships = options.get('all_ships', False)
        min_samples = options['min_samples']
        dry_run = options['dry_run']

        if not import_dir.exists():
            raise CommandError(f"Import directory not found: {import_dir}")

        # Get list of reconciled files
        reconciled_files = list(import_dir.glob('*_cluster_*_reconciled.md'))

        if not reconciled_files:
            raise CommandError(f"No reconciled files found in {import_dir}")

        self.stdout.write(f"Found {len(reconciled_files)} reconciled files\n")

        imported = []
        skipped = []
        errors = []

        for filepath in reconciled_files:
            try:
                result = self._import_reconciled_file(filepath, min_samples, dry_run)
                if result == 'skipped':
                    skipped.append(filepath.name)
                elif result == 'imported':
                    imported.append(filepath.name)
                elif result != 'dry_run':  # Don't count dry-run as error
                    errors.append(f"{filepath.name}: {result}")
            except Exception as e:
                errors.append(f"{filepath.name}: {e}")

        # Output summary
        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
        self.stdout.write(f"Import Summary")
        self.stdout.write(self.style.SUCCESS(f"{'=' * 60}"))
        self.stdout.write(f"Total files: {len(reconciled_files)}")
        self.stdout.write(f"Imported: {len(imported)}")
        self.stdout.write(f"Skipped: {len(skipped)}")
        self.stdout.write(f"Errors: {len(errors)}")

        if imported:
            self.stdout.write(self.style.SUCCESS("\nImported:"))
            for name in imported:
                self.stdout.write(f"  ✓ {name}")

        if skipped:
            self.stdout.write(self.style.WARNING("\nSkipped (below sample threshold):"))
            for name in skipped:
                self.stdout.write(f"  - {name}")

        if errors:
            self.stdout.write(self.style.ERROR("\nErrors:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a DRY RUN. No fittings were saved."))

    def _import_reconciled_file(self, filepath: Path, min_samples: int, dry_run: bool):
        """Import a single reconciled markdown file."""
        with open(filepath, 'r') as f:
            content = f.read()

        # Parse the reconciled file
        ship_name, cluster_id, sample_count, eft_content, provenance_links = self._parse_reconciled(content)

        if sample_count < min_samples:
            return 'skipped'

        # Build provenance description
        description = self._build_provenance_description(
            ship_name, cluster_id, sample_count, provenance_links
        )

        # Extract the EFT content between ```
        eft_match = re.search(r'```(.+?)```', content, re.DOTALL)
        if not eft_match:
            return 'no EFT content found'

        eft_content = eft_match.group(1).strip()

        if dry_run:
            self.stdout.write(f"\nWould import: {filepath.name}")
            self.stdout.write(f"  Ship: {ship_name}, Cluster: {cluster_id}, Samples: {sample_count}")
            self.stdout.write(f"  Description length: {len(description)} chars")
            return 'dry_run'

        # Import the fitting (parse clean EFT, then set description separately)
        try:
            fitting = FittingImporter.import_from_string(
                eft_content,  # Just the EFT content, not with description prepended
                'eft',
                auto_detect=False,
            )

            # Update with cluster metadata and provenance description
            fitting.description = description
            fitting.cluster_id = cluster_id
            fitting.fit_count = sample_count
            fitting.save()

            self.stdout.write(f"  ✓ Imported: {ship_name} - Cluster {cluster_id}\n")

            return 'imported'

        except Exception as e:
            raise Exception(f"Failed to import: {e}")

    def _parse_reconciled(self, content: str):
        """Parse a reconciled markdown file to extract components."""
        lines = content.split('\n')

        # Extract ship name and cluster from header
        header_match = re.match(r'# (.+?) - Cluster (\d+)', lines[0])
        if not header_match:
            raise ValueError("Invalid header format")

        ship_name = header_match.group(1)
        cluster_id = int(header_match.group(2))

        # Extract sample count
        samples_match = re.search(r'\((\d+) lossmails sampled\)', lines[2])
        sample_count = int(samples_match.group(1)) if samples_match else 0

        # Extract EFT content
        eft_match = re.search(r'```(.+?)```', content, re.DOTALL)
        eft_content = eft_match.group(1).strip() if eft_match else ''

        # Extract provenance links from the table
        links_match = re.search(r'\|\s+Fit ID\s+\|.*?\n((?:\|.*?\n)+)', content)
        provenance_links = []
        if links_match:
            table_lines = links_match.group(1)
            for line in table_lines.split('\n'):
                link_match = re.search(r'\[(\d+)\]\((https://zkillboard\.com/kill/\d+/)\)\]', line)
                if link_match:
                    killmail_id = link_match.group(1)
                    url = link_match.group(2)
                    provenance_links.append((killmail_id, url))

        return ship_name, cluster_id, sample_count, eft_content, provenance_links

    def _build_provenance_description(self, ship_name: str, cluster_id: int,
                                  sample_count: int, provenance_links):
        """Build the provenance description for a meta fit."""
        lines = []

        lines.append(f"Meta fit for {ship_name} (Cluster {cluster_id})")
        lines.append("")
        lines.append(f"**Source**: EVEWire Career Research Module")
        lines.append("")
        lines.append(f"**Method**: Cluster analysis of {sample_count} lossmails from zkillboard")
        lines.append("")

        if provenance_links:
            lines.append("**Example Lossmails**:")
            lines.append("")
            for killmail_id, url in provenance_links[:5]:  # Limit to 5 examples
                lines.append(f"- [Killmail {killmail_id}]({url})")
            lines.append("")
            lines.append(f"*{len(provenance_links)} total samples analyzed for this cluster*")
            lines.append("")

        lines.append("*This fit represents the most common configuration found in this cluster.*")
        lines.append("*Updated automatically based on empirical killmail data.*")

        return '\n'.join(lines)
