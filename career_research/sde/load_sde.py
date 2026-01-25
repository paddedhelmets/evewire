#!/usr/bin/env python3
"""
Load EVE SDE into PostgreSQL for the career_research database.

This loads the minimal SDE tables needed for clustering analysis:
- invTypes: All item types (ships, modules, etc.)
- invGroups: Item groups (ship classes, etc.)
- invCategories: Item categories (Ships, Modules, etc.)

Usage:
    python load_sde.py
    python load_sde.py --sde-path /path/to/sde.sqlite3
    python load_sde.py --replace  # Replace existing data
"""

import sys
import argparse
import sqlite3
from pathlib import Path

import psycopg

# Tables to load and their column mappings
# Key: sqlite table name, Value: (postgres table name, column mappings)
TABLES = {
    'core_itemcategory': ('sde.invcategories', {
        'categoryID': 'category_id',
        'categoryName': 'name',
        'iconID': 'icon_id',
        'published': 'published',
    }),
    'core_itemgroup': ('sde.invgroups', {
        'groupID': 'group_id',
        'categoryID': 'category_id',
        'groupName': 'name',
        'iconID': 'icon_id',
        'anchored': 'anchored',
        'anchorable': 'anchorable',
        'fittableNonSingleton': 'fittable_non_singleton',
        'published': 'published',
    }),
    'core_itemtype': ('sde.invtypes', {
        'typeID': 'type_id',
        'groupID': 'group_id',
        'typeName': 'name',
        'description': 'description',
        'mass': 'mass',
        'volume': 'volume',
        'capacity': 'capacity',
        'portionSize': 'portion_size',
        'raceID': 'race_id',
        'basePrice': 'base_price',
        'published': 'published',
        'marketGroupID': 'market_group_id',
        'iconID': 'icon_id',
        'soundID': 'sound_id',
        'graphicID': 'graphic_id',
    }),
}


def load_table(sqlite_conn, pg_conn, sqlite_table: str, pg_table: str, columns: dict, replace: bool = False):
    """
    Load a table from SQLite to PostgreSQL.

    Args:
        sqlite_conn: SQLite connection
        pg_conn: PostgreSQL connection
        sqlite_table: Source table name in SQLite
        pg_table: Target table name in Postgres (schema.table)
        columns: Column name mapping {sqlite_name: pg_name}
        replace: Drop and recreate table if True
    """
    print(f"Loading {sqlite_table} -> {pg_table}...")

    # Get column info from SQLite
    cur = sqlite_conn.cursor()
    cur.execute(f"PRAGMA table_info({sqlite_table})")
    sqlite_columns = {row[1]: row[2] for row in cur.fetchall()}

    # Build column lists
    sqlite_cols = list(columns.keys())
    pg_cols = list(columns.values())

    # Create table in Postgres
    pg_cur = pg_conn.cursor()

    if replace:
        pg_cur.execute(f"DROP TABLE IF EXISTS {pg_table} CASCADE")
        pg_conn.commit()
        print(f"  Dropped existing {pg_table}")

    # Check if table exists
    pg_cur.execute(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'sde'
            AND table_name = '{pg_table.split('.')[-1]}'
        )
    """)
    table_exists = pg_cur.fetchone()[0]

    if not table_exists:
        # Build CREATE TABLE statement
        col_defs = []
        for sqlite_col in sqlite_cols:
            pg_col = columns[sqlite_col]
            sqlite_type = sqlite_columns[sqlite_col].upper()

            # Map SQLite types to PostgreSQL types
            if 'INT' in sqlite_type:
                pg_type = 'INTEGER'
            elif 'FLOAT' in sqlite_type or 'DECIMAL' in sqlite_type:
                pg_type = 'DOUBLE PRECISION'
            elif 'BOOLEAN' in sqlite_type:
                pg_type = 'BOOLEAN'
            elif 'BLOB' in sqlite_type:
                pg_type = 'BYTEA'
            else:
                pg_type = 'TEXT'

            # Add PRIMARY KEY for typeID, groupID, categoryID
            if pg_col.endswith('_id') and sqlite_col == sqlite_cols[0]:
                pg_type += ' PRIMARY KEY'

            col_defs.append(f"{pg_col} {pg_type}")

        create_sql = f"""
            CREATE TABLE {pg_table} (
                {', '.join(col_defs)}
            )
        """
        pg_cur.execute(create_sql)
        pg_conn.commit()
        print(f"  Created {pg_table}")

    # Load data
    cur.execute(f"SELECT {', '.join(sqlite_cols)} FROM {sqlite_table} WHERE published = 1")
    rows = cur.fetchall()

    if not rows:
        print(f"  No rows to load")
        return

    # Build INSERT statement
    # SQLite returns 0/1 for booleans, use CASE for conversion
    placeholders_list = []
    for i, pg_col in enumerate(pg_cols):
        sqlite_col = sqlite_cols[i]
        col_type = sqlite_columns[sqlite_col].upper()
        if col_type == 'BOOLEAN':
            placeholders_list.append("(CASE WHEN %s = 1 THEN TRUE ELSE FALSE END)")
        else:
            placeholders_list.append("%s")
    placeholders = ', '.join(placeholders_list)
    insert_sql = f"INSERT INTO {pg_table} ({', '.join(pg_cols)}) VALUES ({placeholders})"

    # Batch insert
    batch_size = 10000
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        pg_cur.executemany(insert_sql, batch)
        pg_conn.commit()
        print(f"  Loaded {min(i + batch_size, len(rows))}/{len(rows)} rows")

    print(f"  Done: {len(rows)} rows")


def create_indexes(pg_conn):
    """Create indexes for common queries."""
    print("Creating indexes...")

    pg_cur = pg_conn.cursor()

    indexes = [
        "CREATE INDEX IF NOT EXISTS invtypes_name_idx ON sde.invtypes (name)",
        "CREATE INDEX IF NOT EXISTS invtypes_group_idx ON sde.invtypes (group_id)",
        "CREATE INDEX IF NOT EXISTS invgroups_category_idx ON sde.invgroups (category_id)",
        "CREATE INDEX IF NOT EXISTS invgroups_anchored_idx ON sde.invgroups (anchored) WHERE anchored = TRUE",
        "CREATE INDEX IF NOT EXISTS invgroups_anchorable_idx ON sde.invgroups (anchorable) WHERE anchorable = TRUE",
    ]

    for idx_sql in indexes:
        try:
            pg_cur.execute(idx_sql)
            pg_conn.commit()
            print(f"  Created: {idx_sql.split('ON')[-1].strip()}")
        except Exception as e:
            print(f"  Index already exists or error: {e}")

    print("  Done")


def main():
    parser = argparse.ArgumentParser(description="Load EVE SDE into PostgreSQL")
    parser.add_argument(
        '--sde-path',
        type=str,
        default='~/data/evewire/eve_sde.sqlite3',
        help='Path to SDE sqlite database',
    )
    parser.add_argument(
        '--db-url',
        type=str,
        default='postgresql://genie@/career_research',
        help='PostgreSQL connection URL',
    )
    parser.add_argument(
        '--replace',
        action='store_true',
        help='Drop and recreate existing tables',
    )
    args = parser.parse_args()

    sde_path = Path(args.sde_path).expanduser()

    if not sde_path.exists():
        print(f"Error: SDE not found at {sde_path}")
        sys.exit(1)

    # Connect to databases
    print(f"Connecting to SDE: {sde_path}")
    sqlite_conn = sqlite3.connect(sde_path)

    print(f"Connecting to Postgres: {args.db_url}")
    pg_conn = psycopg.connect(args.db_url)

    # Create schema
    pg_cur = pg_conn.cursor()
    pg_cur.execute("CREATE SCHEMA IF NOT EXISTS sde")
    pg_conn.commit()
    print("Created schema 'sde'")

    # Load each table
    for sqlite_table, (pg_table, columns) in TABLES.items():
        load_table(
            sqlite_conn,
            pg_conn,
            sqlite_table,
            pg_table,
            columns,
            replace=args.replace,
        )

    # Create indexes
    create_indexes(pg_conn)

    # Close connections
    sqlite_conn.close()
    pg_conn.close()

    print("\nSDE loading complete!")


if __name__ == "__main__":
    main()
