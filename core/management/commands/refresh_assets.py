"""
Management command to manually trigger character assets refresh.

Can be run via cron or systemd timer for periodic refresh.
This is a heavy operation and should be run less frequently than other refreshes.

Usage:
    python manage.py refresh_assets
"""
import logging
from django.core.management.base import BaseCommand
from django_q.tasks import async_task

logger = logging.getLogger('evewire')


class Command(BaseCommand):
    help = 'Trigger character assets refresh (heavy operation)'

    def handle(self, *args, **options):
        result = async_task('core.eve.tasks.refresh_stale_assets')
        self.stdout.write(f'Queued character assets refresh task: {result}')
        self.stdout.write(self.style.SUCCESS('Assets refresh queued'))
