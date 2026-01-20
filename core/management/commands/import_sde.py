"""
Management command to import EVE SDE (Static Data Export).

Uses Fuzzwork Enterprises pre-built SQLite database - the simplest approach.
Downloads the SDE database and copies required tables into our database.
"""

import os
import tempfile
import urllib.request
import bz2
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Download and import EVE SDE data from Fuzzwork SQLite'

    # Fuzzwork SDE SQLite database (compressed)
    SDE_URL = "https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2"

    # Tables we need for skill plans and basic operations
    REQUIRED_TABLES = [
        'invTypes',           # All items (skills, ships, modules)
        'invGroups',          # Item groups
        'invCategories',      # Item categories
        'dgmAttributeTypes',  # Attribute definitions
        'dgmTypeAttributes',  # Item attributes (skill prerequisites!)
        'chrFactions',        # Factions
        'chrRaces',           # Races
        'mapSolarSystems',    # Solar systems
        'staStations',        # Stations
        'invNames',           # Item names
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-download and re-import even if tables exist',
        )
        parser.add_argument(
            '--tables',
            type=str,
            help='Comma-separated list of tables to import (default: all required)',
        )

    def handle(self, *args, **options):
        # Check which tables to import
        if options['tables']:
            tables = [t.strip() for t in options['tables'].split(',')]
        else:
            tables = self.REQUIRED_TABLES

        self.stdout.write(f'Importing {len(tables)} tables from Fuzzwork SDE SQLite database')

        # Download and extract the SDE database
        with tempfile.TemporaryDirectory() as tmpdir:
            sde_path = os.path.join(tmpdir, 'sde.sqlite')

            # Download and decompress
            self.stdout.write('Downloading SDE database (~50MB compressed, ~300MB uncompressed)...')
            try:
                compressed_path = os.path.join(tmpdir, 'sde.sqlite.bz2')
                urllib.request.urlretrieve(self.SDE_URL, compressed_path)

                self.stdout.write('Decompressing (this may take a minute)...')
                with bz2.open(compressed_path, 'rb') as compressed:
                    with open(sde_path, 'wb') as decompressed:
                        decompressed.write(compressed.read())
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to download SDE: {e}'))
                return

            # Copy tables
            imported = 0
            skipped = 0

            for table in tables:
                if self._table_exists(table) and not options['force']:
                    self.stdout.write(self.style.WARNING(f'{table}: skipped (already exists)'))
                    skipped += 1
                    continue

                self.stdout.write(f'{table}: importing...')

                try:
                    rows = self._copy_table(sde_path, table)
                    self.stdout.write(self.style.SUCCESS(f'{table}: imported {rows:,} rows'))
                    imported += 1
                except Exception as e:
                    import traceback
                    self.stdout.write(self.style.ERROR(f'{table}: failed - {e}'))
                    self.stdout.write(traceback.format_exc())

        self.stdout.write(f'\nDone: {imported} imported, {skipped} skipped')

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table already exists and has data."""
        import sqlite3
        db_path = settings.DATABASES['default']['NAME']
        if db_path is None:
            db_path = str(Path(settings.BASE_DIR) / 'db.sqlite3')

        conn = sqlite3.connect(db_path)
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [table_name]).fetchone()
        conn.close()
        return result is not None

    def _copy_table(self, sde_path: str, table_name: str) -> int:
        """Copy a table from SDE database to our database."""
        import sqlite3

        db_path = settings.DATABASES['default']['NAME']
        if db_path is None:
            db_path = str(Path(settings.BASE_DIR) / 'db.sqlite3')

        # Connect to both databases
        sde_conn = sqlite3.connect(sde_path)
        sde_conn.row_factory = sqlite3.Row

        # Get table schema and data from SDE
        sde_cursor = sde_conn.cursor()

        # Get table schema
        sde_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        schema_row = sde_cursor.fetchone()

        if not schema_row:
            raise ValueError(f"Table {table_name} not found in SDE")

        # Convert MySQL/Fuzzwork schema to SQLite-compatible if needed
        create_sql = schema_row['sql']
        create_sql = create_sql.replace('`', '')  # Remove MySQL backticks
        create_sql = create_sql.replace('COLLATE utf8mb4_unicode_ci', '')  # Remove MySQL collation
        create_sql = create_sql.replace('DEFAULT CURRENT_TIMESTAMP', '')  # Remove MySQL defaults
        create_sql = create_sql.replace('ON UPDATE CURRENT_TIMESTAMP', '')  # Remove MySQL triggers

        # Drop existing table if any
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        # Create table
        with connection.cursor() as cursor:
            cursor.execute(create_sql)

        # Get row count
        sde_cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        row_count = sde_cursor.fetchone()['cnt']

        # Copy data in batches
        batch_size = 1000
        offset = 0
        total_copied = 0

        with connection.cursor() as cursor:
            while True:
                sde_cursor.execute(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
                rows = sde_cursor.fetchall()

                if not rows:
                    break

                # Build and execute INSERT statement
                columns = [desc[0] for desc in sde_cursor.description]
                placeholders = ', '.join(['?'] * len(columns))
                insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                cursor.executemany(insert_sql, rows)
                total_copied += len(rows)
                offset += batch_size

        return total_copied
