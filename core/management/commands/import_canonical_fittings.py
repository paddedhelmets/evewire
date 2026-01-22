"""
Import canonical fittings from zkillboard clustering analysis.

Loads cluster results from the career_research PostgreSQL database
and creates Fitting entries with FittingEntry for each module slot.

Usage:
    python manage.py import_canonical_fittings [--ship_id ID] [--limit N]
    python manage.py import_canonical_fittings --ship_id 12005  # Ishtar
    python manage.py import_canonical_fittings --ship_id 626    # Vexor
"""

import sys
import logging
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / 'career_research'))

from clustering.analyze import ClusterAnalyzer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import canonical fittings from zkillboard clustering analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ship_id',
            type=int,
            help='Import only this ship type ID',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of clusters per ship to import',
        )
        parser.add_argument(
            '--min_size',
            type=int,
            default=5,
            help='Minimum cluster size to import',
        )
        parser.add_argument(
            '--dry_run',
            action='store_true',
            help='Show what would be imported without making changes',
        )

    def handle(self, *args, **options):
        ship_id = options.get('ship_id')
        limit = options['limit']
        min_size = options['min_size']
        dry_run = options['dry_run']

        analyzer = ClusterAnalyzer()

        if ship_id:
            ships_to_process = [(ship_id, analyzer.get_ship_name(ship_id))]
        else:
            # Get top ships by fit count
            popular = analyzer.find_popular_ships(limit=20)
            ships_to_process = [(sid, name) for sid, name, _ in popular]

        self.stdout.write(f"Processing {len(ships_to_process)} ships...")

        for sid, ship_name in ships_to_process:
            self._process_ship(analyzer, sid, ship_name, limit, min_size, dry_run)

        self.stdout.write(self.style.SUCCESS("Done!"))

    def _process_ship(self, analyzer, ship_id: int, ship_name: str,
                     limit: int, min_size: int, dry_run: bool):
        """Process one ship and import its clusters."""
        self.stdout.write(f"\nProcessing {ship_name} ({ship_id})...")

        canonical_fits = analyzer.analyze_ship_clusters(ship_id, limit=limit)

        for canonical in canonical_fits:
            if canonical.fit_count < min_size:
                self.stdout.write(f"  Skipping cluster {canonical.cluster_id}: "
                                 f"only {canonical.fit_count} fits (< {min_size})")
                continue

            self._import_canonical_fit(canonical, dry_run)

    def _import_canonical_fit(self, canonical, dry_run: bool):
        """Import one canonical fit as a Fitting."""
        from core.doctrines.models import Fitting, FittingEntry

        # Generate fitting name
        fitting_name = f"{canonical.ship_name} Cluster {canonical.cluster_id}"

        if dry_run:
            self.stdout.write(f"  [DRY RUN] Would create: {fitting_name}")
            self._show_fit_summary(canonical)
            return

        with transaction.atomic():
            # Check if already exists
            existing = Fitting.objects.filter(
                ship_type_id=canonical.ship_id,
                cluster_id=canonical.cluster_id
            ).first()

            if existing:
                self.stdout.write(f"  Skipping {fitting_name}: already exists")
                return

            # Create fitting
            fitting = Fitting.objects.create(
                name=fitting_name,
                description=f"Canonical fit from cluster {canonical.cluster_id}",
                ship_type_id=canonical.ship_id,
                cluster_id=canonical.cluster_id,
                fit_count=canonical.fit_count,
                avg_similarity=canonical.avg_similarity,
                is_active=True,
            )

            # Create entries for each slot
            entries = []
            for slot_type, slot_name, modules in [
                ('high', 'High', canonical.high_slots),
                ('med', 'Med', canonical.med_slots),
                ('low', 'Low', canonical.low_slots),
                ('rig', 'Rig', canonical.rig_slots),
                ('subsystem', 'Subsystem', canonical.subsystem_slots),
            ]:
                for position, (type_id, name, count) in enumerate(modules):
                    usage_pct = 100 * count / canonical.fit_count
                    entries.append(FittingEntry(
                        fitting=fitting,
                        slot_type=slot_type,
                        position=position,
                        module_type_id=type_id,
                        usage_count=count,
                        usage_percentage=usage_pct,
                    ))

            FittingEntry.objects.bulk_create(entries)

            self.stdout.write(self.style.SUCCESS(
                f"  Created {fitting_name} with {len(entries)} module entries"
            ))

    def _show_fit_summary(self, canonical):
        """Show a summary of the fit."""
        self.stdout.write(f"    Ship: {canonical.ship_name}")
        self.stdout.write(f"    Fits: {canonical.fit_count}")
        self.stdout.write(f"    Highs: {len(canonical.high_slots)}")
        self.stdout.write(f"    Meds: {len(canonical.med_slots)}")
        self.stdout.write(f"    Lows: {len(canonical.low_slots)}")
        self.stdout.write(f"    Rigs: {len(canonical.rig_slots)}")
