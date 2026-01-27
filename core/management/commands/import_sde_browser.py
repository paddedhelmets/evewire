"""
Management command to import EVE SDE for the SDE Browser.

This is SEPARATE from Evewire's SDE import (import_sde.py).

Differences:
- Uses evesde_ table prefix (not core_)
- Exact 1:1 copies of SDE tables (no modifications)
- managed=False models (Django doesn't manage schema)
- For read-only SDE browsing, not app logic

Usage:
    python manage.py import_sde_browser              # Import all browser tables
    python manage.py import_sde_browser --tables=invTypes,invGroups  # Specific tables
    python manage.py import_sde_browser --list       # List available tables
    python manage.py import_sde_browser --force       # Re-import even if exists
"""

import os
import tempfile
import urllib.request
import bz2
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Import EVE SDE tables for the SDE Browser (evesde_ prefix)'

    # Fuzzwork SDE SQLite database (compressed)
    SDE_URL = "https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2"

    # Tables available for import (expand as needed)
    # Maps SDE table name to our evesde_ prefixed table name
    AVAILABLE_TABLES = {
        # === Items & hierarchy ===
        'invTypes': 'evesde_invtypes',
        'invGroups': 'evesde_invgroups',
        'invCategories': 'evesde_invcategories',
        'invMarketGroups': 'evesde_invmarketgroups',
        'invMetaGroups': 'evesde_invmetagroups',

        # === Attributes (dogma) ===
        'dgmAttributeTypes': 'evesde_dgmattributetypes',
        'dgmTypeAttributes': 'evesde_dgmatypeattributes',
        'dgmEffects': 'evesde_dgmeffects',
        'dgmTypeEffects': 'evesde_dgmtypeeffects',
        'dgmSkillAttributes': 'evesde_dgmskillattributes',
        'dgmExprExpressions': 'evesde_dgmexprexpressions',
        'dgmExprInfo': 'evesde_dgmexprinfo',

        # === Skills ===
        'chrSkills': 'evesde_chrskills',
        'chrSkillLevelAttributes': 'evesde_chrskilllevelattributes',
        'chrCertificates': 'evesde_chrcertificates',
        'chrCertSkills': 'evesde_chrcertskills',

        # === Universe/map ===
        'mapRegions': 'evesde_mapregions',
        'mapConstellations': 'evesde_mapconstellations',
        'mapSolarSystems': 'evesde_mapsolarsystems',
        'mapLocationWormholeClasses': 'evesde_maplocationwormholeclasses',

        # === Stations ===
        'staStations': 'evesde_stastations',
        'staOperationServices': 'evesde_staoperationservices',
        'staStationTypes': 'evesde_stastationtypes',

        # === Corporations/Factions ===
        'crpNPCCorporations': 'evesde_crpnpccorporations',
        'crpNPCCorporationTrades': 'evesde_crpnpccorporationtrades',
        'chrFactions': 'evesde_chrfactions',
        'chrRaces': 'evesde_chrraces',
        'chrAncestries': 'evesde_chrancestries',
        'chrBloodlines': 'evesde_chrbloodlines',

        # === Agents ===
        'agtAgents': 'evesde_agtagents',
        'agtAgentTypes': 'evesde_agtagenttypes',
        'agtResearchAgents': 'evesde_agtresearchagents',

        # === Blueprints ===
        'invBlueprints': 'evesde_invblueprints',
        'industryActivity': 'evesde_industryactivity',
        'industryActivityMaterials': 'evesde_industryactivitymaterials',
        'industryActivityProducts': 'evesde_industryactivityproducts',
        'industryActivitySkills': 'evesde_industryactivityskills',

        # === Control towers (POS) ===
        'invControlTowerResources': 'evesde_invcontroltowerresources',

        # === Universe landmarks ===
        'mapLandmarks': 'evesde_maplandmarks',
        'mapUniverse': 'evesde_mapuniverse',

        # === Prices (market history base) ===
        'history': 'evesde_history',  # optional, big table
    }

    # Default set for browser (core tables)
    DEFAULT_TABLES = {
        'invTypes',
        'invGroups',
        'invCategories',
        'invMarketGroups',
        'invMetaGroups',
        'dgmAttributeTypes',
        'dgmTypeAttributes',
        'dgmEffects',
        'dgmTypeEffects',
        'chrSkills',
        'chrSkillLevelAttributes',
        'chrCertificates',
        'mapRegions',
        'mapConstellations',
        'mapSolarSystems',
        'staStations',
        'crpNPCCorporations',
        'chrFactions',
        'chrRaces',
        'agtAgents',
        'invBlueprints',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--tables',
            type=str,
            help='Comma-separated list of SDE tables to import (default: DEFAULT_TABLES)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Import all available tables',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List available tables and exit',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-import even if table exists',
        )

    def handle(self, *args, **options):
        # List mode
        if options['list']:
            return self._list_tables()

        # Determine which tables to import
        if options['all']:
            table_map = self.AVAILABLE_TABLES
        elif options['tables']:
            tables = [t.strip() for t in options['tables'].split(',')]
            table_map = {t: self.AVAILABLE_TABLES.get(t) for t in tables if t in self.AVAILABLE_TABLES}
            if len(table_map) != len(tables):
                missing = set(tables) - set(self.AVAILABLE_TABLES.keys())
                self.stdout.write(self.style.WARNING(f'Unknown tables: {missing}'))
        else:
            table_map = {k: self.AVAILABLE_TABLES[k] for k in self.DEFAULT_TABLES if k in self.AVAILABLE_TABLES}

        self.stdout.write(f'Importing {len(table_map)} tables for SDE Browser')

        # Download and import
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

            # Import each table
            imported = 0
            skipped = 0
            failed = 0

            for sde_table, evesde_table in sorted(table_map.items()):
                if self._table_exists(evesde_table) and not options['force']:
                    self.stdout.write(f'  {sde_table} -> {evesde_table}: skipped (exists)')
                    skipped += 1
                    continue

                self.stdout.write(f'  {sde_table} -> {evesde_table}: importing...')

                try:
                    rows = self._copy_table(sde_path, sde_table, evesde_table)
                    self.stdout.write(self.style.SUCCESS(f'  {sde_table} -> {evesde_table}: {rows:,} rows'))
                    imported += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  {sde_table}: failed - {e}'))
                    failed += 1

        self.stdout.write(f'\nDone: {imported} imported, {skipped} skipped, {failed} failed')

    def _list_tables(self):
        """List all available tables."""
        self.stdout.write('Available SDE tables for import:')
        self.stdout.write('')

        for category in self._get_table_categories():
            self.stdout.write(f'\n{category["name"]}:')
            for table in category['tables']:
                sde_table = table['sde']
                evesde_table = self.AVAILABLE_TABLES[sde_table]
                exists = self._table_exists(evesde_table)
                status = '✓' if exists else ' '
                default = ' (default)' if sde_table in self.DEFAULT_TABLES else ''
                self.stdout.write(f'  [{status}] {sde_table:40s} -> {evesde_table}{default}')

    def _get_table_categories(self):
        """Group tables by category for listing."""
        return [
            {
                'name': 'Items & Hierarchy',
                'tables': [
                    {'sde': 'invTypes', 'desc': 'All item types (ships, modules, etc.)'},
                    {'sde': 'invGroups', 'desc': 'Item groups'},
                    {'sde': 'invCategories', 'desc': 'Item categories'},
                    {'sde': 'invMarketGroups', 'desc': 'Market groups'},
                    {'sde': 'invMetaGroups', 'desc': 'Meta groups (Tech I/II, faction, etc.)'},
                ]
            },
            {
                'name': 'Attributes (Dogma)',
                'tables': [
                    {'sde': 'dgmAttributeTypes', 'desc': 'Attribute type definitions'},
                    {'sde': 'dgmTypeAttributes', 'desc': 'Item attributes'},
                    {'sde': 'dgmEffects', 'desc': 'Effect definitions'},
                    {'sde': 'dgmTypeEffects', 'desc': 'Item effects'},
                    {'sde': 'dgmSkillAttributes', 'desc': 'Skill bonus attributes'},
                ]
            },
            {
                'name': 'Skills & Certificates',
                'tables': [
                    {'sde': 'chrSkills', 'desc': 'Skill definitions'},
                    {'sde': 'chrSkillLevelAttributes', 'desc': 'SP per level'},
                    {'sde': 'chrCertificates', 'desc': 'Certificates'},
                    {'sde': 'chrCertSkills', 'desc': 'Certificate skill requirements'},
                ]
            },
            {
                'name': 'Universe / Map',
                'tables': [
                    {'sde': 'mapRegions', 'desc': 'Regions'},
                    {'sde': 'mapConstellations', 'desc': 'Constellations'},
                    {'sde': 'mapSolarSystems', 'desc': 'Solar systems'},
                    {'sde': 'mapLocationWormholeClasses', 'desc': 'Wormhole classes'},
                ]
            },
            {
                'name': 'Stations',
                'tables': [
                    {'sde': 'staStations', 'desc': 'Stations'},
                    {'sde': 'staOperationServices', 'desc': 'Station services'},
                    {'sde': 'staStationTypes', 'desc': 'Station types'},
                ]
            },
            {
                'name': 'Corporations & Factions',
                'tables': [
                    {'sde': 'crpNPCCorporations', 'desc': 'NPC corporations'},
                    {'sde': 'chrFactions', 'desc': 'Factions'},
                    {'sde': 'chrRaces', 'desc': 'Races'},
                    {'sde': 'chrAncestries', 'desc': 'Ancestries'},
                    {'sde': 'chrBloodlines', 'desc': 'Bloodlines'},
                ]
            },
            {
                'name': 'Agents',
                'tables': [
                    {'sde': 'agtAgents', 'desc': 'Agents'},
                    {'sde': 'agtAgentTypes', 'desc': 'Agent types'},
                    {'sde': 'agtResearchAgents', 'desc': 'Research agents'},
                ]
            },
            {
                'name': 'Industry / Blueprints',
                'tables': [
                    {'sde': 'invBlueprints', 'desc': 'Blueprint metadata'},
                    {'sde': 'industryActivity', 'desc': 'Industry activities'},
                    {'sde': 'industryActivityMaterials', 'desc': 'Activity materials'},
                    {'sde': 'industryActivityProducts', 'desc': 'Activity products'},
                    {'sde': 'industryActivitySkills', 'desc': 'Activity skills'},
                ]
            },
        ]

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table already exists and has data."""
        import sqlite3
        db_path = settings.DATABASES['default']['NAME']

        conn = sqlite3.connect(db_path)
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [table_name]).fetchone()
        if result:
            count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            conn.close()
            return count_result[0] > 0
        conn.close()
        return False

    def _copy_table(self, sde_path: str, sde_table: str, evesde_table: str) -> int:
        """Copy a table from SDE database to evesde_ prefixed table."""
        import sqlite3
        import re

        db_path = settings.DATABASES['default']['NAME']

        # Connect to SDE database
        sde_conn = sqlite3.connect(sde_path)
        sde_conn.row_factory = sqlite3.Row

        # Connect to our Django database
        django_conn = sqlite3.connect(db_path)
        django_cursor = django_conn.cursor()

        # Get table schema from SDE
        sde_cursor = sde_conn.cursor()
        sde_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{sde_table}'")
        schema_row = sde_cursor.fetchone()

        if not schema_row:
            sde_conn.close()
            django_conn.close()
            raise ValueError(f"Table {sde_table} not found in SDE")

        create_sql = schema_row['sql']

        # Clean up SQL for SQLite compatibility
        create_sql = create_sql.replace('"', '')
        create_sql = create_sql.replace('COLLATE utf8mb4_unicode_ci', '')
        create_sql = create_sql.replace('DEFAULT CURRENT_TIMESTAMP', '')
        create_sql = create_sql.replace('ON UPDATE CURRENT_TIMESTAMP', '')

        # Replace table name with evesde_ prefixed name
        create_sql = re.sub(
            r'CREATE TABLE (?:IF NOT EXISTS )?\w+ \(',
            f'CREATE TABLE {evesde_table} (',
            create_sql
        )

        # Drop existing table if any
        django_cursor.execute(f"DROP TABLE IF EXISTS {evesde_table}")

        # Create table
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

            placeholders = ', '.join(['?'] * len(original_columns))
            insert_sql = f"INSERT INTO {evesde_table} ({', '.join(original_columns)}) VALUES ({placeholders})"

            django_cursor.executemany(insert_sql, rows)
            total_copied += len(rows)
            offset += batch_size

        django_conn.commit()
        sde_conn.close()
        django_conn.close()

        return total_copied
