"""
Fetch station names from ESI /universe/names/ endpoint.

The SDE staStations table has NULL stationname values in modern SDE.
This command fetches station names from ESI's /universe/names/ endpoint.
"""

import logging
from django.core.management.base import BaseCommand
from django.db import connection
from django_q.tasks import async_task

logger = logging.getLogger('evewire')


class Command(BaseCommand):
    help = 'Fetch station names from ESI /universe/names/ endpoint'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of station IDs to fetch per ESI request (max 1000)',
        )

    def handle(self, *args, **options):
        batch_size = min(options['batch_size'], 1000)  # ESI max is 1000

        with connection.cursor() as cursor:
            # Get all station IDs that have NULL names
            cursor.execute("SELECT stationid FROM core_station WHERE stationname IS NULL ORDER BY stationid")
            station_ids = [row[0] for row in cursor.fetchall()]

        if not station_ids:
            self.stdout.write(self.style.SUCCESS('All stations already have names!'))
            return

        self.stdout.write(f'Fetching names for {len(station_ids)} stations in batches of {batch_size}')

        # Queue background tasks for each batch
        queued = 0
        for i in range(0, len(station_ids), batch_size):
            batch = station_ids[i:i + batch_size]
            async_task('core.management.commands.fetch_station_names._fetch_batch', batch)
            queued += 1

        self.stdout.write(self.style.SUCCESS(f'Queued {queued} batch task(s) to fetch {len(station_ids)} station names'))
        self.stdout.write('Note: Check django-q cluster logs for progress. Names will be updated in background.')


def _fetch_batch(station_ids):
    """Fetch a batch of station names from ESI and update the database."""
    from core.esi_client import ESIClient
    from django.db import connection
    import logging

    logger = logging.getLogger('evewire')

    try:
        # Post station IDs to /universe/names/
        # This returns a list of {"id": int, "name": str} objects
        response = ESIClient.post_universe_names(station_ids)

        if response.status_code != 200:
            logger.error(f'Failed to fetch names for {len(station_ids)} stations: {response.status_code}')
            return False

        names_data = response.data

        # Build a map of station_id -> name
        name_map = {item['id']: item['name'] for item in names_data if 'id' in item and 'name' in item}

        # Update the database
        with connection.cursor() as cursor:
            for station_id, name in name_map.items():
                cursor.execute(
                    "UPDATE core_station SET stationname = %s WHERE stationid = %s",
                    [name, station_id]
                )

        logger.info(f'Updated {len(name_map)} station names')
        return len(name_map)

    except Exception as e:
        logger.error(f'Failed to fetch station names: {e}')
        return False
