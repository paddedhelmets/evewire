"""
Populate station names from invNames table.

The SDE staStations table has NULL stationname values.
This command joins invNames with core_station to populate the names.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Populate station names from invNames table'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write('Dry run mode - showing what would be updated:')

        with connection.cursor() as cursor:
            # Check how many stations have NULL names
            cursor.execute("SELECT COUNT(*) FROM core_station WHERE stationname IS NULL")
            null_count = cursor.fetchone()[0]
            self.stdout.write(f'Stations with NULL names: {null_count}')

            # Check how many matching names we have in invNames
            cursor.execute("""
                SELECT COUNT(*)
                FROM core_station s
                INNER JOIN core_invnames n ON s.stationid = n.itemid
                WHERE s.stationname IS NULL
            """)
            match_count = cursor.fetchone()[0]
            self.stdout.write(f'Matching names in invNames: {match_count}')

            if dry_run:
                # Show a sample of what would be updated
                cursor.execute("""
                    SELECT s.stationid, n.itemname
                    FROM core_station s
                    INNER JOIN core_invnames n ON s.stationid = n.itemid
                    WHERE s.stationname IS NULL
                    LIMIT 5
                """)
                self.stdout.write('\nSample updates:')
                for row in cursor.fetchall():
                    self.stdout.write(f'  Station {row[0]}: "{row[1]}"')
                return

            # Update station names from invNames
            self.stdout.write('Updating station names...')
            cursor.execute("""
                UPDATE core_station s
                SET stationname = n.itemname
                FROM core_invnames n
                WHERE s.stationid = n.itemid
                AND s.stationname IS NULL
            """)
            updated = cursor.rowcount
            self.stdout.write(self.style.SUCCESS(f'Updated {updated} station names'))

            # Verify the update
            cursor.execute("SELECT COUNT(*) FROM core_station WHERE stationname IS NULL")
            remaining = cursor.fetchone()[0]
            if remaining > 0:
                self.stdout.write(self.style.WARNING(f'{remaining} stations still have NULL names (not in invNames)'))
            else:
                self.stdout.write(self.style.SUCCESS('All stations now have names!'))
