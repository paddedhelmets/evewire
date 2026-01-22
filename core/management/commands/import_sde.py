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
    # Maps SDE table name to Django model table name
    REQUIRED_TABLES = {
        'invTypes': 'core_itemtype',
        'invGroups': 'core_itemgroup',
        'invCategories': 'core_itemcategory',
        'dgmAttributeTypes': 'core_attributetype',
        'dgmTypeAttributes': 'core_typeattribute',
        'chrFactions': 'core_faction',
        'chrRaces': 'core_itemtype',  # Races are item types
        'mapSolarSystems': 'core_solarsystem',
        'staStations': 'core_station',
    }

    # Column name mappings from SDE to Django (camelCase to snake_case)
    # Only include columns that exist in the SDE source table
    COLUMN_MAPPINGS = {
        'core_typeattribute': {
            'typeID': 'type_id',
            'attributeID': 'attribute_id',
            'valueInt': 'value_int',
            'valueFloat': 'value_float',
        },
        'core_attributetype': {
            'attributeID': 'id',
            'attributeName': 'name',
            'description': 'description',
            'iconID': 'icon_id',
            'defaultValue': 'default_value',
            'published': 'published',
            'displayName': 'display_name',
            'unitID': 'unit_id',
            'stackable': 'stackable',
            'highIsGood': 'high_is_good',
            'categoryID': 'category_id',
        },
        'core_itemtype': {
            'typeID': 'id',
            'typeName': 'name',
            'description': 'description',
            'groupID': 'group_id',
            'mass': 'mass',
            'volume': 'volume',
            'capacity': 'capacity',
            'portionSize': 'portion_size',
            'published': 'published',
        },
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-download and re-import even if tables exist',
        )
        parser.add_argument(
            '--tables',
            type=str,
            help='Comma-separated list of SDE tables to import (default: all required)',
        )

    def handle(self, *args, **options):
        # Check which tables to import
        if options['tables']:
            tables = [t.strip() for t in options['tables'].split(',')]
            table_map = {t: self.REQUIRED_TABLES.get(t, t) for t in tables}
        else:
            table_map = self.REQUIRED_TABLES

        self.stdout.write(f'Importing {len(table_map)} tables from Fuzzwork SDE SQLite database')

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

            for sde_table, django_table in table_map.items():
                if self._table_exists(django_table) and not options['force']:
                    self.stdout.write(self.style.WARNING(f'{sde_table} -> {django_table}: skipped (already exists)'))
                    skipped += 1
                    continue

                self.stdout.write(f'{sde_table} -> {django_table}: importing...')

                try:
                    rows = self._copy_table(sde_path, sde_table, django_table)
                    self.stdout.write(self.style.SUCCESS(f'{sde_table} -> {django_table}: imported {rows:,} rows'))
                    imported += 1
                except Exception as e:
                    import traceback
                    self.stdout.write(self.style.ERROR(f'{sde_table}: failed - {e}'))
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
        if result:
            # Check if table has data
            count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            conn.close()
            return count_result[0] > 0
        conn.close()
        return False

    def _copy_table(self, sde_path: str, sde_table: str, django_table: str) -> int:
        """Copy a table from SDE database to our Django database."""
        import sqlite3

        db_path = settings.DATABASES['default']['NAME']
        if db_path is None:
            db_path = str(Path(settings.BASE_DIR) / 'db.sqlite3')

        # Connect to SDE database
        sde_conn = sqlite3.connect(sde_path)
        sde_conn.row_factory = sqlite3.Row

        # Connect to our Django database (raw sqlite for direct table manipulation)
        django_conn = sqlite3.connect(db_path)
        django_cursor = django_conn.cursor()

        # Get table schema and data from SDE
        sde_cursor = sde_conn.cursor()

        # Get table schema from SDE
        sde_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{sde_table}'")
        schema_row = sde_cursor.fetchone()

        if not schema_row:
            sde_conn.close()
            django_conn.close()
            raise ValueError(f"Table {sde_table} not found in SDE")

        # Convert MySQL/Fuzzwork schema to Django-compatible format
        create_sql = schema_row['sql']
        # Remove double quotes around identifiers (SQLite uses double quotes for column/table names)
        create_sql = create_sql.replace('"', '')
        create_sql = create_sql.replace('COLLATE utf8mb4_unicode_ci', '')  # Remove MySQL collation
        create_sql = create_sql.replace('DEFAULT CURRENT_TIMESTAMP', '')  # Remove MySQL defaults
        create_sql = create_sql.replace('ON UPDATE CURRENT_TIMESTAMP', '')  # Remove MySQL triggers

        # Replace the table name in CREATE statement with Django table name
        # Handle both "CREATE TABLE name" and "CREATE TABLE IF NOT EXISTS name"
        import re
        create_sql = re.sub(
            r'CREATE TABLE (?:IF NOT EXISTS )?\w+ \(',
            f'CREATE TABLE {django_table} (',
            create_sql
        )

        # Rename columns to match Django model names (camelCase to snake_case)
        column_map = self.COLUMN_MAPPINGS.get(django_table, {})
        for sde_col, django_col in column_map.items():
            create_sql = re.sub(rf'\b{sde_col}\b', django_col, create_sql)

        # Drop existing Django table if any
        django_cursor.execute(f"DROP TABLE IF EXISTS {django_table}")

        # Create table with Django name
        django_cursor.execute(create_sql)

        # Get row count from SDE
        sde_cursor.execute(f"SELECT COUNT(*) as cnt FROM {sde_table}")
        row_count = sde_cursor.fetchone()[0]

        # Copy data in batches
        batch_size = 1000
        offset = 0
        total_copied = 0

        # Get column mapping for this table if any
        column_map = self.COLUMN_MAPPINGS.get(django_table, {})

        while True:
            sde_cursor.execute(f"SELECT * FROM {sde_table} LIMIT {batch_size} OFFSET {offset}")
            rows = sde_cursor.fetchall()

            if not rows:
                break

            # Build and execute INSERT statement for Django table
            # Apply column name mapping if defined
            original_columns = [desc[0] for desc in sde_cursor.description]
            if column_map:
                # Map SDE column names to Django column names
                target_columns = [column_map.get(col, col) for col in original_columns]
            else:
                target_columns = original_columns

            placeholders = ', '.join(['?'] * len(target_columns))
            insert_sql = f"INSERT INTO {django_table} ({', '.join(target_columns)}) VALUES ({placeholders})"

            django_cursor.executemany(insert_sql, rows)
            total_copied += len(rows)
            offset += batch_size

        # Special post-processing for TypeAttribute - add id column for Django
        if django_table == 'core_typeattribute':
            self.stdout.write(f'  Adding id column for Django compatibility...')
            django_cursor.execute(f"ALTER TABLE {django_table} ADD COLUMN id INTEGER")
            # Populate id with rowid
            django_cursor.execute(f"UPDATE {django_table} SET id = rowid")

        # Commit changes and close connections
        django_conn.commit()
        sde_conn.close()
        django_conn.close()

        return total_copied
