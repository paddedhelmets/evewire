"""
Sideload data for EVE SDE import.

The garveen eve-sde-converter includes the factionID column in crpNPCCorporations
but does not populate it with data. This module provides sideload functionality
to populate factionID from a separate data source.

Source: EVE Static Data Export (older versions have factionID populated)
"""
import os
from pathlib import Path
from django.db import connection

# Path to sideload data files
SIDELOAD_DIR = Path(__file__).parent


def apply_corp_faction_id_sideload(table_name: str = 'evesde_crpnpccorporations') -> int:
    """
    Apply factionID sideload to NPC corporations table.

    This updates the factionID column in crpNPCCorporations with data from
    corp_faction_ids.sql, which contains corporation -> faction mappings
    extracted from a complete EVE SDE.

    Args:
        table_name: The target table name (evesde_crpnpccorporations or core_crpnpccorporations)

    Returns:
        Number of rows updated
    """
    sideload_path = SIDELOAD_DIR / 'corp_faction_ids.sql'

    if not sideload_path.exists():
        raise FileNotFoundError(f"Sideload file not found: {sideload_path}")

    with open(sideload_path, 'r') as f:
        sql_content = f.read()

    # Read the SQL file and execute the UPDATE statements
    # Skip comments and BEGIN/COMMIT, execute UPDATEs
    update_count = 0
    with connection.cursor() as cursor:
        for line in sql_content.split('\n'):
            line = line.strip()
            if line.startswith('UPDATE ') and line.startswith(f'UPDATE {table_name}'):
                cursor.execute(line)
                update_count += cursor.rowcount
        connection.commit()

    return update_count
