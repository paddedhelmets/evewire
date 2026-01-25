"""
Management command to refresh player structure data from ESI.

Usage:
    python manage.py refresh_structures              # Refresh all stale structures
    python manage.py refresh_structures --all        # Refresh all structures (force)
    python manage.py refresh_structures --id 12345   # Refresh specific structure
    python manage.py refresh_structures --dry-run    # Show what would be refreshed
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from django_q.tasks import async_task

logger = logging.getLogger('evewire')


class Command(BaseCommand):
    help = 'Refresh player structure names from ESI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            dest='all',
            help='Refresh all structures (not just stale ones)',
        )
        parser.add_argument(
            '--id',
            type=int,
            dest='structure_id',
            help='Refresh a specific structure by ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be refreshed without actually doing it',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            dest='sync',
            help='Run synchronously (wait for completion before returning)',
        )

    def handle(self, *args, **options):
        from core.eve.models import Structure

        # Handle specific structure
        if options['structure_id']:
            return self.refresh_one(options['structure_id'], options)

        # Handle all or stale structures
        return self.refresh_many(options)

    def refresh_one(self, structure_id: int, options: dict) -> str:
        """Refresh a single structure."""
        from core.eve.tasks import refresh_structure

        self.stdout.write(f"Refreshing structure {structure_id}...")

        if options['dry_run']:
            self.stdout.write(f"[DRY RUN] Would refresh structure {structure_id}")
            return

        if options['sync']:
            # Run synchronously
            result = refresh_structure(structure_id)
            if result:
                self.stdout.write(self.style.SUCCESS(f"✓ Refreshed structure {structure_id}"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ Failed to refresh structure {structure_id}"))
        else:
            # Queue as background task
            async_task('core.eve.tasks.refresh_structure', structure_id)
            self.stdout.write(f"Queued refresh task for structure {structure_id}")

    def refresh_many(self, options: dict) -> str:
        """Refresh multiple structures."""
        from core.eve.models import Structure

        # Build query
        if options['all']:
            structures = Structure.objects.all()
            self.stdout.write(f"Refreshing ALL structures ({structures.count()} total)...")
        else:
            # Only stale structures
            stale_cutoff = timezone.now() - timezone.timedelta(days=7)
            error_cutoff = timezone.now() - timezone.timedelta(hours=1)

            structures = Structure.objects.filter(
                models.Q(last_sync_status='ok', last_updated__lt=stale_cutoff)
                | models.Q(last_sync_status='error', last_updated__lt=error_cutoff)
            )
            self.stdout.write(f"Refreshing stale structures ({structures.count()} total)...")

        if options['dry_run']:
            for structure in structures:
                age = (timezone.now() - structure.last_updated).total_seconds()
                age_hours = age / 3600
                self.stdout.write(
                    f"[DRY RUN] Would refresh: {structure.name} ({structure.structure_id}) "
                    f"- last updated {age_hours:.1f} hours ago"
                )
            return

        # Queue refresh tasks
        queued = 0
        for structure in structures:
            if options['sync']:
                # Run synchronously (one by one)
                from core.eve.tasks import refresh_structure
                result = refresh_structure(structure.structure_id)
                if result:
                    self.stdout.write(self.style.SUCCESS(f"✓ {structure.name}"))
                else:
                    self.stdout.write(self.style.ERROR(f"✗ {structure.name}"))
            else:
                # Queue as background tasks
                async_task('core.eve.tasks.refresh_structure', structure.structure_id)
                queued += 1

        if not options['sync']:
            self.stdout.write(
                self.style.SUCCESS(f"Queued {queued} structure refresh tasks")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Refresh complete"))
