"""
Management command to import EVE SDE (Static Data Export).

Uses garveen's eve-sde-converter pre-built SQLite database.
Downloads the SDE database and copies required tables into the main database.

SDE tables use the core_ prefix (e.g., core_itemtype) to avoid naming conflicts
with Django application tables.

NOTE: Models use db_column to map to SDE column names, so we can copy
tables directly without any column name transformations.
"""

import json
import os
import tempfile
import urllib.request
import bz2
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Download and import EVE SDE data from garveen eve-sde-converter'

    # Garveen's eve-sde-converter GitHub releases API
    RELEASES_API = "https://api.github.com/repos/garveen/eve-sde-converter/releases"

    # Tables we need for skill plans and basic operations
    # Maps SDE table name to Django model table name
    REQUIRED_TABLES = {
        'invTypes': 'core_itemtype',
        'invGroups': 'core_itemgroup',
        'invCategories': 'core_itemcategory',
        'dgmAttributeTypes': 'core_attributetype',
        'dgmTypeAttributes': 'core_typeattribute',
        'chrFactions': 'core_faction',
        # Note: chrRaces are already in invTypes, not imported separately
        'mapSolarSystems': 'core_solarsystem',
        'mapRegions': 'core_region',
        'staStations': 'core_station',
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
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without doing anything',
        )
        parser.add_argument(
            '--init',
            action='store_true',
            help='Initialize the SDE database (download full SDE to shared location)',
        )
        parser.add_argument(
            '--sde-version',
            type=str,
            dest='sde_version',
            help='Specific SDE version tag (e.g., 3171578-01ec212). Default: latest from GitHub.',
        )

    def handle(self, *args, **options):
        # Get the shared SDE database path
        sde_db_path = Path(settings.DATABASES['default']['NAME'])

        self.stdout.write(f'SDE Database: {sde_db_path}')

        # Handle --init mode: download full SDE to shared location
        if options['init']:
            return self._init_sde(sde_db_path)

        # Check which tables to import
        if options['tables']:
            tables = [t.strip() for t in options['tables'].split(',')]
            table_map = {t: self.REQUIRED_TABLES.get(t, t) for t in tables}
        else:
            table_map = self.REQUIRED_TABLES

        # Get SDE download URL
        version = options.get('sde_version')
        if version:
            sde_url = f"https://github.com/garveen/eve-sde-converter/releases/download/sde-{version}/sde.sqlite.bz2"
            self.stdout.write(f'Using SDE version: {version}')
        else:
            sde_url = self._get_latest_sde_url()
            if not sde_url:
                self.stdout.write(self.style.ERROR('Failed to fetch latest SDE release. Use --sde-version to specify a version.'))
                return

        self.stdout.write(f'Importing {len(table_map)} tables from garveen eve-sde-converter')

        # Dry run mode
        if options['dry_run']:
            self.stdout.write('Dry run mode - would import:')
            for sde_table, django_table in table_map.items():
                exists = self._table_exists(django_table)
                status = 'exists' if exists else 'would create'
                self.stdout.write(f'  {sde_table} -> {django_table}: {status}')
            return

        # Download and extract the SDE database
        with tempfile.TemporaryDirectory() as tmpdir:
            sde_path = os.path.join(tmpdir, 'sde.sqlite')

            # Download and decompress
            self.stdout.write(f'Downloading SDE database...')
            try:
                compressed_path = os.path.join(tmpdir, 'sde.sqlite.bz2')
                urllib.request.urlretrieve(sde_url, compressed_path)

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

    def _init_sde(self, target_path: Path) -> None:
        """Initialize the SDE database by downloading the full SDE to the shared location."""
        import shutil
        import sqlite3

        self.stdout.write(f'Initializing SDE database at {target_path}')
        self.stdout.write('This will download the full SDE (~300MB) and may take several minutes.')

        # Get latest SDE URL
        sde_url = self._get_latest_sde_url()
        if not sde_url:
            self.stdout.write(self.style.ERROR('Failed to fetch latest SDE release.'))
            return

        # Create parent directory if it doesn't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Download to temp file first
        with tempfile.TemporaryDirectory() as tmpdir:
            compressed_path = os.path.join(tmpdir, 'sde.sqlite.bz2')
            decompressed_path = os.path.join(tmpdir, 'sde.sqlite')

            self.stdout.write('Downloading SDE database...')
            try:
                urllib.request.urlretrieve(sde_url, compressed_path)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to download SDE: {e}'))
                return

            self.stdout.write('Decompressing...')
            try:
                with bz2.open(compressed_path, 'rb') as compressed:
                    with open(decompressed_path, 'wb') as decompressed:
                        decompressed.write(compressed.read())
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to decompress SDE: {e}'))
                return

            # Verify the database
            self.stdout.write('Verifying database...')
            try:
                conn = sqlite3.connect(decompressed_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                conn.close()
                self.stdout.write(f'Database contains {table_count} tables')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Database verification failed: {e}'))
                return

            # Move to target location (backup existing if present)
            if target_path.exists():
                backup_path = target_path.with_suffix('.sqlite3.backup')
                self.stdout.write(f'Backing up existing database to {backup_path}')
                shutil.move(str(target_path), str(backup_path))

            self.stdout.write(f'Installing SDE to {target_path}')
            shutil.move(decompressed_path, str(target_path))

        self.stdout.write(self.style.SUCCESS('SDE database initialized successfully'))
        self.stdout.write('You can now run import_sde without --init to add additional tables.')

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table already exists and has data."""
        import sqlite3
        db_path = settings.DATABASES['default']['NAME']

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
        """
        Copy a table from SDE database to our Django database.

        NOTE: Models use db_column to map to SDE column names, so we can copy
        tables directly without column name transformations. The only change
        needed is renaming the table itself.
        """
        import sqlite3

        db_path = settings.DATABASES['default']['NAME']

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

        # Get the CREATE TABLE statement
        create_sql = schema_row['sql']

        # Remove double quotes around identifiers (SQLite uses double quotes for column/table names)
        create_sql = create_sql.replace('"', '')
        # Remove MySQL-specific clauses that Fuzzwork might include
        create_sql = create_sql.replace('COLLATE utf8mb4_unicode_ci', '')
        create_sql = create_sql.replace('DEFAULT CURRENT_TIMESTAMP', '')
        create_sql = create_sql.replace('ON UPDATE CURRENT_TIMESTAMP', '')

        # Replace the table name in CREATE statement with Django table name
        # Handle both "CREATE TABLE name" and "CREATE TABLE IF NOT EXISTS name"
        import re
        create_sql = re.sub(
            r'CREATE TABLE (?:IF NOT EXISTS )?\w+ \(',
            f'CREATE TABLE {django_table} (',
            create_sql
        )

        # Drop existing Django table if any
        django_cursor.execute(f"DROP TABLE IF EXISTS {django_table}")

        # Create table with Django name (keeping SDE column names)
        django_cursor.execute(create_sql)

        # Get row count from SDE
        sde_cursor.execute(f"SELECT COUNT(*) as cnt FROM {sde_table}")
        row_count = sde_cursor.fetchone()[0]

        # Copy data in batches
        batch_size = 1000
        offset = 0
        total_copied = 0

        # Get column names from SDE
        sde_cursor.execute(f"SELECT * FROM {sde_table} LIMIT 1")
        original_columns = [desc[0] for desc in sde_cursor.description]

        while True:
            sde_cursor.execute(f"SELECT * FROM {sde_table} LIMIT {batch_size} OFFSET {offset}")
            rows = sde_cursor.fetchall()

            if not rows:
                break

            # Build and execute INSERT statement
            placeholders = ', '.join(['?'] * len(original_columns))
            insert_sql = f"INSERT INTO {django_table} ({', '.join(original_columns)}) VALUES ({placeholders})"

            django_cursor.executemany(insert_sql, rows)
            total_copied += len(rows)
            offset += batch_size

        # Special post-processing for TypeAttribute - add id column for Django
        # Django models require a primary key named 'id', but SDE uses composite key
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

    def _get_latest_sde_url(self) -> str | None:
        """Fetch the latest SDE release URL from GitHub."""
        try:
            req = urllib.request.Request(
                self.RELEASES_API,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                releases = json.loads(response.read().decode())

            if not releases:
                return None

            # Get the latest release
            latest = releases[0]
            tag_name = latest.get('tag_name', '')

            # Tag format should be sde-{BUILD}-{HASH}
            if not tag_name.startswith('sde-'):
                return None

            version = tag_name[4:]  # Strip 'sde-' prefix
            url = f"https://github.com/garveen/eve-sde-converter/releases/download/sde-{version}/sde.sqlite.bz2"

            self.stdout.write(f'Latest SDE version: {version}')
            return url

        except Exception:
            return None
