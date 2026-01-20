"""
Management command to import EVE SDE (Static Data Export).

Uses Fuzzwork Enterprises pre-built SQLite database - the community standard.
Downloads the SDE database and copies required tables into our database.
"""

import os
import tempfile
import urllib.request
import bz2
import sqlite3 as sqlite
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Download and import EVE SDE data from Fuzzwork SQLite'

    # Fuzzwork SDE pre-built SQLite database (compressed)
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

            # Connect to SDE database
            try:
                sde_conn = sqlite.connect(sde_path)
                sde_conn.row_factory = sqlite.Row
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to open SDE database: {e}'))
                return

            # Import each table
            imported = 0
            skipped = 0

            for table in tables:
                if self._table_exists(table) and not options['force']:
                    self.stdout.write(self.style.WARNING(f'{table}: skipped (already exists)'))
                    skipped += 1
                    continue

                self.stdout.write(f'{table}: importing...')

                try:
                    rows = self._copy_table(sde_conn, table)
                    self.stdout.write(self.style.SUCCESS(f'{table}: imported {rows:,} rows'))
                    imported += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'{table}: failed - {e}'))

            sde_conn.close()

        self.stdout.write(f'\nDone: {imported} imported, {skipped} skipped')

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table already exists and has data."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                [table_name]
            )
            return cursor.fetchone() is not None

    def _copy_table(self, sde_conn, table_name: str) -> int:
        """Copy a table from SDE database to our database."""
        # Get schema and data from SDE
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
        create_sql = create_sql.replace('COLLATE utf8mb4_general_ci', '')
        create_sql = create_sql.replace('DEFAULT CURRENT_TIMESTAMP', '')
        create_sql = create_sql.replace('ON UPDATE CURRENT_TIMESTAMP', '')

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

                # Build INSERT statement
                columns = [desc[0] for desc in sde_cursor.description]
                placeholders = ', '.join(['?' for _ in columns])
                columns_str = ', '.join(columns)

                for row in rows:
                    cursor.execute(
                        f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})",
                        tuple(row)
                    )
                    total_copied += 1

                offset += batch_size
                self.stdout.write(f'  Progress: {total_copied}/{row_count}', ending='\r')

            connection.commit()
            self.stdout.write('')  # New line after progress

        return total_copied
