"""
Shared utilities for SDE import operations.

Handles PostgreSQL-specific considerations for importing EVE SDE data
from garveen's eve-sde-converter SQLite database.
"""

import re
import sqlite3
from django.conf import settings
from django.db import connections


def get_sde_db_path():
    """
    Get the path where the SDE SQLite database should be stored.
    For SQLite Django databases, stores alongside the DB file.
    For PostgreSQL, stores in ~/data/evewire/.
    """
    db_engine = settings.DATABASES['default']['ENGINE']
    db_name = settings.DATABASES['default']['NAME']

    if 'sqlite' in db_engine:
        from pathlib import Path
        return Path(db_name).parent / f"{Path(db_name).stem}_sde.sqlite"
    else:
        # For PostgreSQL, store SDE in a data directory
        from pathlib import Path
        return Path.home() / 'data' / 'evewire' / 'sde.sqlite'


def table_exists(table_name: str, table_prefix: str = 'core_') -> bool:
    """
    Check if a table already exists and has data.
    Works with both SQLite and PostgreSQL.
    """
    db_engine = settings.DATABASES['default']['ENGINE']
    full_table = f"{table_prefix}{table_name}"

    if 'postgresql' in db_engine:
        # PostgreSQL check
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, [full_table])
            if not cursor.fetchone()[0]:
                return False
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {full_table}")
                return cursor.fetchone()[0] > 0
            except:
                return False
    else:
        # SQLite fallback
        db_path = settings.DATABASES['default']['NAME']
        conn = sqlite3.connect(db_path)
        result = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{full_table}'").fetchone()
        if result:
            count_result = conn.execute(f"SELECT COUNT(*) FROM {full_table}").fetchone()
            conn.close()
            return count_result[0] > 0
        conn.close()
        return False


def prepare_sql_for_postgresql(create_sql: str, sde_table: str, django_table: str,
                               is_dgm_type_attributes: bool = False) -> str:
    """
    Convert SQLite CREATE TABLE syntax to PostgreSQL-compatible SQL.

    Handles:
    - Type conversions (INTEGER → BIGINT, REAL → DOUBLE PRECISION, etc.)
    - System column conflicts (xmin, xmax, cmin, cmax, x, y, z)
    - Composite primary key handling
    - Backtick removal
    - Collation and timestamp clause removal
    """
    # Remove quotes and backticks
    create_sql = create_sql.replace('"', '').replace('`', '')

    # Remove MySQL-specific clauses
    create_sql = create_sql.replace('COLLATE utf8mb4_unicode_ci', '')
    create_sql = create_sql.replace('DEFAULT CURRENT_TIMESTAMP', '')
    create_sql = create_sql.replace('ON UPDATE CURRENT_TIMESTAMP', '')

    # Rename PostgreSQL system column conflicts (case-insensitive)
    create_sql = re.sub(r'\bxmin\b', 'xmin_coord', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bxmax\b', 'xmax_coord', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bcmin\b', 'cmin_coord', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bcmax\b', 'cmax_coord', create_sql, flags=re.IGNORECASE)

    # Replace table name (don't include the opening parenthesis in the match)
    create_sql = re.sub(
        r'CREATE TABLE (?:IF NOT EXISTS )?(\w+)',
        f'CREATE TABLE {django_table}',
        create_sql
    )

    # Type conversions (order matters! Do these BEFORE coordinate renames)
    create_sql = create_sql.replace(' REAL', ' DOUBLE PRECISION')
    # Be careful not to double-convert DOUBLE PRECISION
    create_sql = re.sub(r'\bdouble\b', 'DOUBLE PRECISION', create_sql, flags=re.IGNORECASE)

    # Handle INTEGER → BIGINT for specific tables that need it
    if is_dgm_type_attributes or 'dgmTypeAttributes' in sde_table:
        # Replace all INTEGER with BIGINT
        create_sql = re.sub(r'\bINTEGER\b', 'BIGINT', create_sql, flags=re.IGNORECASE)
    else:
        # More selective conversions for other tables
        # IMPORTANT: Do ID-specific conversions FIRST, before the generic PRIMARY KEY replacement
        create_sql = re.sub(r'\btypeID INTEGER', 'typeID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bvalueInt INTEGER', 'valueInt BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bvalue_integer INTEGER', 'value_integer BIGINT', create_sql, flags=re.IGNORECASE)
        # Corporation and faction tables may have large IDs
        create_sql = re.sub(r'\bcorporationID INTEGER', 'corporationID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bfactionID INTEGER', 'factionID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bsolarSystemID INTEGER', 'solarSystemID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bregionID INTEGER', 'regionID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bconstellationID INTEGER', 'constellationID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bstationID INTEGER', 'stationID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bceoID INTEGER', 'ceoID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bcreatorID INTEGER', 'creatorID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\ballianceID INTEGER', 'allianceID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\ballyID INTEGER', 'allyID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\b(investorID\d) INTEGER', r'\1 BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\bfriendID INTEGER', 'friendID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\benemyID INTEGER', 'enemyID BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\biconID INTEGER', 'iconID BIGINT', create_sql, flags=re.IGNORECASE)
        # Share and price columns can exceed INTEGER range
        create_sql = re.sub(r'\bpublicShares INTEGER', 'publicShares BIGINT', create_sql, flags=re.IGNORECASE)
        create_sql = re.sub(r'\b(investorShares\d) INTEGER', r'\1 BIGINT', create_sql, flags=re.IGNORECASE)
        # Now handle remaining INTEGER PRIMARY KEY → SERIAL (but only if not already converted to BIGINT)
        create_sql = create_sql.replace(' INTEGER PRIMARY KEY', ' SERIAL PRIMARY KEY')
        create_sql = create_sql.replace(' BIGINT PRIMARY KEY', ' BIGINT PRIMARY KEY')  # No change, keeps BIGINT
        # Remaining INTEGER stays as INTEGER

    # Remove BLOB
    create_sql = create_sql.replace(' BLOB', ' BYTEA')

    # Rename coordinate columns AFTER type conversions (to avoid double-converting DOUBLE PRECISION)
    # x DOUBLE PRECISION -> x_coord DOUBLE PRECISION
    create_sql = re.sub(r'\bx\s+', 'x_coord ', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\by\s+', 'y_coord ', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bz\s+', 'z_coord ', create_sql, flags=re.IGNORECASE)

    return create_sql


def get_renamed_columns(original_columns: list) -> list:
    """
    Get the list of column names after renaming for PostgreSQL compatibility.
    Handles system columns and coordinate columns.
    """
    renamed = []
    for col in original_columns:
        col_lower = col.lower()
        if col_lower in ('xmin', 'xmax', 'cmin', 'cmax'):
            renamed.append(f"{col}_coord")
        elif col_lower in ('x', 'y', 'z'):
            renamed.append(f"{col}_coord")
        else:
            renamed.append(col)
    return renamed
