"""
Management command to manually trigger character refresh tasks.

Can be run via cron or systemd timer for periodic refresh.
Usage:
    python manage.py refresh_characters              # Refresh all stale data
    python manage.py refresh_characters --metadata    # Metadata only
    python manage.py refresh_characters --assets      # Assets only
    python manage.py refresh_characters --skills      # Skills only
"""
import logging
from django.core.management.base import BaseCommand
from django_q.tasks import async_task

logger = logging.getLogger('evewire')


class Command(BaseCommand):
    help = 'Trigger character refresh tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--metadata',
            action='store_true',
            dest='metadata',
            help='Refresh character metadata (location, wallet, orders)',
        )
        parser.add_argument(
            '--assets',
            action='store_true',
            dest='assets',
            help='Refresh character assets',
        )
        parser.add_argument(
            '--skills',
            action='store_true',
            dest='skills',
            help='Refresh character skills/queue',
        )

    def handle(self, *args, **options):
        queued = 0

        if not any([options['metadata'], options['assets'], options['skills']]):
            # Refresh all if nothing specified
            options['metadata'] = True
            options['assets'] = True
            options['skills'] = True

        if options['metadata']:
            result = async_task('core.eve.tasks.refresh_stale_characters')
            self.stdout.write(f'Queued character metadata refresh task: {result}')
            queued += 1

        if options['assets']:
            result = async_task('core.eve.tasks.refresh_stale_assets')
            self.stdout.write(f'Queued character assets refresh task: {result}')
            queued += 1

        if options['skills']:
            result = async_task('core.eve.tasks.refresh_stale_skills')
            self.stdout.write(f'Queued character skills refresh task: {result}')
            queued += 1

        self.stdout.write(self.style.SUCCESS(f'Queued {queued} refresh task(s)'))
