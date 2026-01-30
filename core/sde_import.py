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
    Get the path to the SDE SQLite database.

    Priority order:
    1. Local eve-sde-converter output (for parallel development)
    2. Shared cached SDE (~/data/evewire/sde.sqlite)
    3. For SQLite Django databases, store alongside the DB file
    """
    from pathlib import Path

    # 1. Check for local converter output (parallel development)
    local_converter = Path.home() / 'projects' / 'eve-sde-converter' / 'output' / 'sde.sqlite'
    if local_converter.exists():
        return local_converter

    # 2. Check for shared cached SDE
    shared_sde = Path.home() / 'data' / 'evewire' / 'sde.sqlite'
    if shared_sde.exists():
        return shared_sde

    # 3. Fall back to default location based on database engine
    db_engine = settings.DATABASES['default']['ENGINE']
    db_name = settings.DATABASES['default']['NAME']

    if 'sqlite' in db_engine:
        return Path(db_name).parent / f"{Path(db_name).stem}_sde.sqlite"
    else:
        # For PostgreSQL, store SDE in a data directory
        return shared_sde


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
                               is_dgm_type_attributes: bool = False,
                               quote_identifiers: bool = False) -> str:
    """
    Convert SQLite CREATE TABLE syntax to PostgreSQL-compatible SQL.

    Handles:
    - Type conversions (INTEGER → BIGINT, REAL → DOUBLE PRECISION, etc.)
    - System column conflicts (xmin, xmax, cmin, cmax, x, y, z)
    - Composite primary key handling
    - Backtick removal
    - Collation and timestamp clause removal
    - Identifier quoting (to preserve case for Django db_column mappings)

    Args:
        quote_identifiers: If True, quote all identifiers to preserve case.
                          Required for SDE browser models that use db_column='camelCase'.
    """
    # Remove quotes and backticks
    create_sql = create_sql.replace('"', '').replace('`', '')

    # Remove MySQL-specific clauses
    create_sql = create_sql.replace('COLLATE utf8mb4_unicode_ci', '')
    create_sql = create_sql.replace('DEFAULT CURRENT_TIMESTAMP', '')
    create_sql = create_sql.replace('ON UPDATE CURRENT_TIMESTAMP', '')

    # Rename columns that will conflict with PostgreSQL system columns after lowercasing
    # xMin -> xmin would conflict, so rename to xmin_coord (matching our system column handling)
    # Use case-insensitive matching to catch xMin, XMIN, etc.
    create_sql = re.sub(r'\bxmin\b', 'xmin_coord', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bxmax\b', 'xmax_coord', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bymin\b', 'ymin_coord', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bymax\b', 'ymax_coord', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bzmin\b', 'zmin_coord', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bzmax\b', 'zmax_coord', create_sql, flags=re.IGNORECASE)
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
    # DECIMAL -> NUMERIC for PostgreSQL
    create_sql = re.sub(r'\bDECIMAL\b', 'NUMERIC', create_sql, flags=re.IGNORECASE)

    # Remove MySQL-specific CHECK constraints that assume INTEGER for boolean columns
    # These will be recreated automatically by PostgreSQL for BOOLEAN columns
    # Pattern: CHECK (columnName in (0,1)) or CHECK (scattered in (0,1))
    create_sql = re.sub(r',\s*CONSTRAINT\s+"?\w+?"?\s+CHECK\s*\([^)]+in\s+\(0,1\)\)', '', create_sql, flags=re.IGNORECASE)

    # Convert INTEGER boolean columns to BOOLEAN
    # These columns store 0/1 but Django expects boolean
    create_sql = re.sub(r'\bpublished INTEGER', 'published BOOLEAN', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\banchored INTEGER', 'anchored BOOLEAN', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\banchorable INTEGER', 'anchorable BOOLEAN', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bfittableNonSingleton INTEGER', 'fittableNonSingleton BOOLEAN', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\buseBasePrice INTEGER', 'useBasePrice BOOLEAN', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bhasTypes INTEGER', 'hasTypes BOOLEAN', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bscattered INTEGER', 'scattered BOOLEAN', create_sql, flags=re.IGNORECASE)
    # Note: tinyint(1) from MySQL/MariaDB also maps to boolean
    create_sql = re.sub(r'\b(\w+)\s+tinyint\(1\)', r'\1 BOOLEAN', create_sql, flags=re.IGNORECASE)

    # Rename coordinate columns AFTER type conversions (to avoid double-converting DOUBLE PRECISION)
    # x DOUBLE PRECISION -> x_coord DOUBLE PRECISION
    create_sql = re.sub(r'\bx\s+', 'x_coord ', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\by\s+', 'y_coord ', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'\bz\s+', 'z_coord ', create_sql, flags=re.IGNORECASE)

    # Quote identifiers to preserve case (for Django db_column mappings)
    if quote_identifiers:
        create_sql = _quote_identifiers_in_sql(create_sql)

    return create_sql


def _quote_identifiers_in_sql(sql: str) -> str:
    """
    Quote identifiers in SQL to preserve case for PostgreSQL.

    PostgreSQL folds unquoted identifiers to lowercase, but Django's db_column
    uses camelCase (e.g., db_column='groupID'). We need to quote identifiers
    to preserve the case.

    This quotes column names and table names while avoiding SQL keywords,
    type names, and other reserved words.
    """
    # SQL keywords and type names that should NOT be quoted
    skip_words = {
        # SQL keywords
        'CREATE', 'TABLE', 'PRIMARY', 'KEY', 'NOT', 'NULL', 'DEFAULT',
        'UNIQUE', 'FOREIGN', 'REFERENCES', 'CONSTRAINT', 'CHECK',
        'SELECT', 'INSERT', 'INTO', 'VALUES', 'WHERE', 'FROM', 'JOIN',
        'ON', 'AND', 'OR', 'NOT', 'IN', 'IS', 'TRUE', 'FALSE',
        # Data types
        'INTEGER', 'BIGINT', 'SMALLINT', 'SERIAL', 'BIGSERIAL',
        'VARCHAR', 'CHAR', 'TEXT', 'BOOLEAN', 'BOOL',
        'REAL', 'DOUBLE', 'PRECISION', 'FLOAT', 'NUMERIC', 'DECIMAL',
        'DATE', 'TIME', 'TIMESTAMP', 'BYTEA', 'BLOB',
        # Other
        'IF', 'NOT', 'EXISTS', 'CASCADE', 'RESTRICT', 'NO', 'ACTION',
        'AUTOINCREMENT', 'ASC', 'DESC', 'LIMIT', 'OFFSET',
    }

    result = []
    # Tokenize by splitting on common delimiters
    tokens = re.split(r'([,\(\)\s]+)', sql)

    for token in tokens:
        # Skip whitespace, punctuation, empty tokens
        if not token or token.isspace() or token in ',()':
            result.append(token)
            continue

        # Check if this looks like an identifier
        # Identifiers: start with letter or underscore, contain letters/digits/underscore
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token):
            upper_token = token.upper()
            # Don't quote SQL keywords or type names
            if upper_token not in skip_words:
                # Quote the identifier to preserve case
                result.append(f'"{token}"')
            else:
                result.append(token)
        else:
            result.append(token)

    return ''.join(result)


def get_renamed_columns(original_columns: list, quote_identifiers: bool = False) -> list:
    """
    Get the list of column names after renaming for PostgreSQL compatibility.

    Handles system columns and coordinate columns.

    Args:
        quote_identifiers: If True, quote column names to preserve case for PostgreSQL.
                          Required for SDE browser models that use db_column='camelCase'.
    """
    renamed = []
    for col in original_columns:
        # Check for system column name matches (case-insensitive)
        # xMin, xmin, XMIN, etc. all conflict with PostgreSQL system columns
        col_lower = col.lower()
        if col_lower in ('xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax', 'cmin', 'cmax'):
            new_col = f"{col_lower}_coord"
        elif col in ('x', 'y', 'z'):
            new_col = f"{col}_coord"
        else:
            new_col = col

        if quote_identifiers:
            renamed.append(f'"{new_col}"')
        else:
            renamed.append(new_col)
    return renamed
