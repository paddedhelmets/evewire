"""
Management command to reorder skill plan entries by prerequisites.

Usage:
    python manage.py reorder_skill_plans              # Reorder all active plans
    python manage.py reorder_skill_plans --plan-id 1  # Reorder specific plan
    python manage.py reorder_skill_plans --dry-run    # Show what would be reordered
    python manage.py reorder_skill_plans --all        # Include inactive plans
"""

import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger('evewire')


class Command(BaseCommand):
    help = 'Reorder skill plan entries based on prerequisite dependencies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--plan-id',
            type=int,
            dest='plan_id',
            help='Reorder a specific skill plan by ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            dest='all',
            help='Include inactive plans (default: active only)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be reordered without actually doing it',
        )

    def handle(self, *args, **options):
        from core.character.models import SkillPlan

        plan_id = options.get('plan_id')
        include_all = options.get('all', False)
        dry_run = options.get('dry_run', False)

        # Build queryset
        if plan_id:
            plans = SkillPlan.objects.filter(id=plan_id)
        else:
            if include_all:
                plans = SkillPlan.objects.all()
            else:
                plans = SkillPlan.objects.filter(is_active=True)

        # Count total plans
        total = plans.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No skill plans found.'))
            return

        self.stdout.write(f'Found {total} skill plan(s) to reorder.')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            for plan in plans:
                entry_count = plan.entries.count()
                self.stdout.write(f'  - Plan {plan.id}: "{plan.name}" ({entry_count} entries)')
            return

        # Reorder each plan
        reordered = 0
        skipped = 0
        errors = 0

        for plan in plans:
            entry_count = plan.entries.count()
            if entry_count == 0:
                self.stdout.write(f'  Skipping plan {plan.id}: "{plan.name}" (no entries)')
                skipped += 1
                continue

            try:
                plan.reorder_by_prerequisites()
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Reordered plan {plan.id}: "{plan.name}" ({entry_count} entries)')
                )
                reordered += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error reordering plan {plan.id}: "{plan.name}": {e}')
                )
                errors += 1

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'Total: {total} plan(s)')
        self.stdout.write(self.style.SUCCESS(f'  Reordered: {reordered}'))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f'  Skipped: {skipped}'))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'  Errors: {errors}'))
