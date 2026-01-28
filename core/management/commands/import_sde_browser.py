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
    python manage.py import_sde_browser --force      # Re-import even if exists
    python manage.py import_sde_browser --sde-version=3171578-01ec212  # Use specific SDE version
"""

import json
import os
import re
import tempfile
import urllib.request
import urllib.error
import bz2
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Import EVE SDE tables for the SDE Browser (evesde_ prefix)'

    # Garveen's eve-sde-converter GitHub releases
    # URL pattern: https://github.com/garveen/eve-sde-converter/releases/download/sde-{BUILD}-{HASH}/sde.sqlite.bz2
    RELEASES_API = "https://api.github.com/repos/garveen/eve-sde-converter/releases"

    # Tables available for import (expand as needed)
    # Maps SDE table name to our evesde_ prefixed table name
    # NOTE: This list only includes tables that actually exist in garveen's SDE schema
    AVAILABLE_TABLES = {
        # === Items & hierarchy ===
        'invTypes': 'evesde_invtypes',
        'invGroups': 'evesde_invgroups',
        'invCategories': 'evesde_invcategories',
        'invMarketGroups': 'evesde_invmarketgroups',
        'invMetaGroups': 'evesde_invmetagroups',
        'invMetaTypes': 'evesde_invmetatypes',
        'invNames': 'evesde_invnames',
        'invTypeMaterials': 'evesde_invtypematerials',
        'invFlags': 'evesde_invflags',
        'invContrabandTypes': 'evesde_invcontrabandtypes',

        # === Assets/Graphics ===
        'eveIcons': 'evesde_eveicons',
        'eveGraphics': 'evesde_evegraphics',
        'eveUnits': 'evesde_eveunits',

        # === Attributes (dogma) ===
        'dgmAttributeTypes': 'evesde_dgmattributetypes',
        'dgmAttributeCategories': 'evesde_dgmattributecategories',
        'dgmTypeAttributes': 'evesde_dgmatypeattributes',
        'dgmEffects': 'evesde_dgmeffects',
        'dgmTypeEffects': 'evesde_dgmtypeeffects',

        # === Certificates ===
        'certCerts': 'evesde_certcerts',
        'certSkills': 'evesde_certskills',
        'certMasteries': 'evesde_certmasteries',

        # === Universe / Map ===
        'mapRegions': 'evesde_mapregions',
        'mapConstellations': 'evesde_mapconstellations',
        'mapSolarSystems': 'evesde_mapsolarsystems',
        'mapDenormalize': 'evesde_mapdenormalize',
        'mapLandmarks': 'evesde_maplandmarks',

        # === Stations ===
        'staStations': 'evesde_stastations',

        # === Corporations/Factions ===
        'crpNPCCorporations': 'evesde_crpnpccorporations',
        'crpActivities': 'evesde_crpactivities',
        'chrFactions': 'evesde_chrfactions',
        'chrRaces': 'evesde_chrraces',
        'chrAncestries': 'evesde_chrancestries',
        'chrBloodlines': 'evesde_chrbloodlines',

        # === Agents ===
        'agtAgents': 'evesde_agtagents',
        'agtAgentTypes': 'evesde_agtagenttypes',
        'agtAgentsInSpace': 'evesde_agtagentsinspace',
        'agtResearchAgents': 'evesde_agtresearchagents',

        # === Blueprints ===
        'industryBlueprints': 'evesde_industryblueprints',

        # === Control towers (POS) ===
        'invControlTowerResources': 'evesde_invcontroltowerresources',

        # === Planet interaction ===
        'planetSchematics': 'evesde_planetschematics',
        'planetSchematicsPinMap': 'evesde_planetschematicspinmap',
        'planetSchematicsTypeMap': 'evesde_planetschematicstypemap',

        # === SKIN system ===
        'skinLicense': 'evesde_skinlicense',
        'skinMaterials': 'evesde_skinmaterials',
        'skinShip': 'evesde_skinship',

        # === Translations ===
        'trnTranslations': 'evesde_trntranslations',
    }

    # Default set for browser (core tables + direct dependencies + useful extras)
    # NOTE: Only includes tables that exist in the current SDE schema
    DEFAULT_TABLES = {
        # Items & hierarchy (core + Level 1/2)
        'invTypes',
        'invGroups',
        'invCategories',
        'invMarketGroups',
        'invMetaGroups',
        'invMetaTypes',
        'invNames',
        'invFlags',
        'invContrabandTypes',
        'invTypeMaterials',

        # Assets/Graphics
        'eveIcons',
        'eveGraphics',
        'eveUnits',

        # Attributes (core + Level 2)
        'dgmAttributeTypes',
        'dgmAttributeCategories',
        'dgmTypeAttributes',
        'dgmEffects',
        'dgmTypeEffects',

        # Map hierarchy (core + Level 2)
        'mapRegions',
        'mapConstellations',
        'mapSolarSystems',
        'mapDenormalize',
        'mapLandmarks',

        # Stations
        'staStations',

        # Corporations/Factions (core + Level 2)
        'crpNPCCorporations',
        'crpActivities',
        'chrFactions',
        'chrRaces',
        'chrAncestries',
        'chrBloodlines',

        # Certificates (Level 2)
        'certCerts',
        'certSkills',
        'certMasteries',

        # Agents (Level 1 + Level 3)
        'agtAgents',
        'agtAgentTypes',
        'agtAgentsInSpace',

        # Blueprints (Level 3)
        'industryBlueprints',

        # Control towers (POS)
        'invControlTowerResources',

        # Planet interaction
        'planetSchematics',
        'planetSchematicsPinMap',
        'planetSchematicsTypeMap',

        # SKIN system
        'skinLicense',
        'skinMaterials',
        'skinShip',
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
        parser.add_argument(
            '--sde-version',
            type=str,
            help='Specific SDE version tag (e.g., 3171578-01ec212). Default: latest from GitHub.',
        )

    def handle(self, *args, **options):
        # List mode
        if options['list']:
            return self._list_tables()

        # Get SDE download URL
        version = options.get('sde_version')
        if version:
            sde_url = f"https://github.com/garveen/eve-sde-converter/releases/download/sde-{version}/sde.sqlite.bz2"
            self.stdout.write(f'Using SDE version: {version}')
        else:
            sde_url = self._get_latest_sde_url()
            if not sde_url:
                self.stdout.write(self.style.ERROR('Failed to fetch latest SDE release. Use --version to specify a version.'))
                return

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
            self.stdout.write(f'Downloading SDE database from {sde_url}...')
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
                self.stdout.write(self.style.WARNING('No releases found'))
                return None

            # Get the latest release
            latest = releases[0]
            tag_name = latest.get('tag_name', '')

            # Tag format should be sde-{BUILD}-{HASH}
            if not tag_name.startswith('sde-'):
                self.stdout.write(self.style.WARNING(f'Unexpected tag format: {tag_name}'))
                return None

            version = tag_name[4:]  # Strip 'sde-' prefix
            url = f"https://github.com/garveen/eve-sde-converter/releases/download/sde-{version}/sde.sqlite.bz2"

            self.stdout.write(f'Latest SDE version: {version}')
            return url

        except urllib.error.URLError as e:
            self.stdout.write(self.style.ERROR(f'Failed to fetch releases: {e}'))
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching latest release: {e}'))
            return None

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
                    {'sde': 'invMetaTypes', 'desc': 'Item variants (Tech II, faction versions)'},
                    {'sde': 'invNames', 'desc': 'Localized item names'},
                    {'sde': 'invFlags', 'desc': 'Item flags (slots, hangars)'},
                    {'sde': 'invContrabandTypes', 'desc': 'Contraband types by faction'},
                    {'sde': 'invTypeMaterials', 'desc': 'Manufacturing requirements'},
                ]
            },
            {
                'name': 'Assets / Graphics',
                'tables': [
                    {'sde': 'eveIcons', 'desc': 'Item icons'},
                    {'sde': 'eveGraphics', 'desc': 'Item graphics'},
                    {'sde': 'eveUnits', 'desc': 'Measurement units for attributes'},
                ]
            },
            {
                'name': 'Attributes (Dogma)',
                'tables': [
                    {'sde': 'dgmAttributeTypes', 'desc': 'Attribute type definitions'},
                    {'sde': 'dgmAttributeCategories', 'desc': 'Attribute categories'},
                    {'sde': 'dgmTypeAttributes', 'desc': 'Item attributes'},
                    {'sde': 'dgmEffects', 'desc': 'Effect definitions'},
                    {'sde': 'dgmTypeEffects', 'desc': 'Item effects'},
                ]
            },
            {
                'name': 'Certificates',
                'tables': [
                    {'sde': 'certCerts', 'desc': 'Certificate definitions'},
                    {'sde': 'certSkills', 'desc': 'Certificate skill requirements'},
                    {'sde': 'certMasteries', 'desc': 'Certificate mastery levels'},
                ]
            },
            {
                'name': 'Universe / Map',
                'tables': [
                    {'sde': 'mapRegions', 'desc': 'Regions'},
                    {'sde': 'mapConstellations', 'desc': 'Constellations'},
                    {'sde': 'mapSolarSystems', 'desc': 'Solar systems'},
                    {'sde': 'mapDenormalize', 'desc': 'Denormalized map data (celestial objects)'},
                    {'sde': 'mapLandmarks', 'desc': 'Space landmarks'},
                ]
            },
            {
                'name': 'Stations',
                'tables': [
                    {'sde': 'staStations', 'desc': 'Stations'},
                ]
            },
            {
                'name': 'Corporations & Factions',
                'tables': [
                    {'sde': 'crpNPCCorporations', 'desc': 'NPC corporations'},
                    {'sde': 'crpActivities', 'desc': 'Corporation activities'},
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
                    {'sde': 'agtAgentsInSpace', 'desc': 'Mission agents in space'},
                    {'sde': 'agtResearchAgents', 'desc': 'Research agents'},
                ]
            },
            {
                'name': 'Industry / Blueprints',
                'tables': [
                    {'sde': 'industryBlueprints', 'desc': 'Blueprint metadata'},
                ]
            },
            {
                'name': 'Control Towers (POS)',
                'tables': [
                    {'sde': 'invControlTowerResources', 'desc': 'POS resources'},
                ]
            },
            {
                'name': 'Planet Interaction',
                'tables': [
                    {'sde': 'planetSchematics', 'desc': 'Planet resource data'},
                    {'sde': 'planetSchematicsPinMap', 'desc': 'Planet pin map'},
                    {'sde': 'planetSchematicsTypeMap', 'desc': 'Planet type map'},
                ]
            },
            {
                'name': 'SKIN System',
                'tables': [
                    {'sde': 'skinLicense', 'desc': 'SKIN licenses'},
                    {'sde': 'skinMaterials', 'desc': 'SKIN materials'},
                    {'sde': 'skinShip', 'desc': 'SKIN ship bindings'},
                ]
            },
            {
                'name': 'Translations',
                'tables': [
                    {'sde': 'trnTranslations', 'desc': 'Localized strings'},
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
        # Handle both `tablename` and tablename formats
        create_sql = re.sub(
            r'CREATE TABLE (?:IF NOT EXISTS )?`?\w+`? \(',
            f'CREATE TABLE {evesde_table} (',
            create_sql
        )

        # Drop existing table if any
        django_cursor.execute(f"DROP TABLE IF EXISTS {evesde_table}")

        # For Django ORM compatibility, add id column if table has composite PK
        # and remove the composite PK constraint
        if 'PRIMARY KEY' in create_sql and ',PRIMARY KEY' in create_sql:
            # This is a composite key table - add id column and remove PK constraint
            # Remove the PRIMARY KEY clause
            create_sql = re.sub(r',\s*PRIMARY KEY \([^)]+\)', '', create_sql, flags=re.IGNORECASE)
            # Add id column as first column
            create_sql = create_sql.replace(f'CREATE TABLE {evesde_table} (',
                                              f'CREATE TABLE {evesde_table} (id INTEGER PRIMARY KEY AUTOINCREMENT, ')

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

        # Apply factionID sideload for crpNPCCorporations
        # The garveen SDE has the factionID column but all values are NULL
        if sde_table == 'crpNPCCorporations':
            try:
                from core.data import apply_corp_faction_id_sideload
                updated = apply_corp_faction_id_sideload(evesde_table)
                self.stdout.write(f'    Applied factionID sideload: {updated} corporations updated')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'    Failed to apply factionID sideload: {e}'))

        return total_copied
