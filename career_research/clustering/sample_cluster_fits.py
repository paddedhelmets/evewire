#!/usr/bin/env python3
"""
Sample actual lossmail fits from clusters for use in evewire.

This addresses the FC feedback about "stochastic view of clusters in latent space"
by providing REAL fits that actual players flew, not synthetic canonical fits.

Usage:
    python sample_cluster_fits.py <ship_id> [--samples N] [--output-dir OUTPUT]
    python sample_cluster_fits.py 12005 --samples 3
    python sample_cluster_fits.py 12005 --samples 5 --output-dir ../meta_fits

Output:
    Creates EFT format files for each sampled fit, named like:
    ishtar_cluster_2_fit_001.eft, ishtar_cluster_2_fit_002.eft, etc.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from clustering.analyze import ClusterAnalyzer


def get_item_name(sde_conn, type_id: int) -> str:
    """Get item name from SDE database."""
    cur = sde_conn.cursor()
    cur.execute('SELECT name FROM core_itemtype WHERE id = ?', (type_id,))
    row = cur.fetchone()
    return row[0] if row else f"Unknown (typeID {type_id})"


def get_fits_from_cluster(conn, ship_id: int, cluster_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Sample actual fits from a cluster."""
    cur = conn.cursor()

    # Get actual lossmail fits from this cluster
    cur.execute('''
        SELECT id, high_slots, med_slots, low_slots, rig_slots, subsystem_slots
        FROM fits
        WHERE ship_id = %s AND cluster_id = %s
        ORDER BY RANDOM()
        LIMIT %s
    ''', (ship_id, cluster_id, limit))

    fits = []
    for row in cur.fetchall():
        fit_id, high, med, low, rig, subsystem = row
        fits.append({
            'fit_id': fit_id,
            'ship_id': ship_id,
            'cluster_id': cluster_id,
            'high_slots': high if high else [],
            'med_slots': med if med else [],
            'low_slots': low if low else [],
            'rig_slots': rig if rig else [],
            'subsystem_slots': subsystem if subsystem else [],
        })

    return fits


def slot_array_to_type_ids(slot_array: List[int]) -> List[int]:
    """Extract type IDs from a slot array."""
    if not slot_array:
        return []
    # Slot arrays are stored as [type_id, type_id, None, ...]
    return [x for x in slot_array if x is not None]


def format_fit_as_eft(sde_conn, ship_id: int, fit: Dict[str, Any], ship_name: str) -> str:
    """Format a fit as EFT format string.

    The fit data comes from zkillboard and contains actual type_ids
    for modules. We need to look up their names from SDE.
    """
    lines = []
    lines.append(f"[{ship_name}, lossmail-{fit['fit_id']}]")

    # Header with empty slots
    all_slots = fit.get('high_slots', []) + fit.get('med_slots', []) + fit.get('low_slots', [])
    empty_count = sum(1 for x in all_slots if x is None)
    if empty_count > 0:
        lines.append("")
        lines.append(f"[empty {empty_count}]")

    # High slots
    highs = slot_array_to_type_ids(fit.get('high_slots', []))
    if highs:
        lines.append("")
        lines.append("")
        for type_id in highs:
            name = get_item_name(sde_conn, type_id)
            lines.append(f"{name}")

    # Med slots
    meds = slot_array_to_type_ids(fit.get('med_slots', []))
    if meds:
        if not highs:
            lines.append("")
            lines.append("")
        for type_id in meds:
            name = get_item_name(sde_conn, type_id)
            lines.append(f"{name}")

    # Low slots
    lows = slot_array_to_type_ids(fit.get('low_slots', []))
    if lows:
        lines.append("")
        lines.append("")
        for type_id in lows:
            name = get_item_name(sde_conn, type_id)
            lines.append(f"{name}")

    # Rigs
    rigs = slot_array_to_type_ids(fit.get('rig_slots', []))
    if rigs:
        lines.append("")
        for type_id in rigs:
            name = get_item_name(sde_conn, type_id)
            lines.append(f"{name}")

    # Subsystems
    subsystems = slot_array_to_type_ids(fit.get('subsystem_slots', []))
    if subsystems:
        lines.append("")
        for type_id in subsystems:
            name = get_item_name(sde_conn, type_id)
            lines.append(f"{name}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Sample real fits from clusters')
    parser.add_argument('ship_id', type=int, help='Ship typeID')
    parser.add_argument('--samples', type=int, default=3, help='Samples per cluster (default: 3)')
    parser.add_argument('--output-dir', type=str, default='output/cluster_samples',
                        help='Output directory for EFT files')
    parser.add_argument('--cluster-id', type=int, help='Only sample from specific cluster')
    args = parser.parse_args()

    ship_id = args.ship_id

    # Connect to databases
    conn = psycopg.connect('postgresql://genie@/career_research')
    sde_path = Path('~/data/evewire/eve_sde.sqlite3').expanduser()

    # Get ship name from SDE
    import sqlite3
    sde_conn = sqlite3.connect(sde_path)
    ship_name = get_item_name(sde_conn, ship_id)

    if ship_name.startswith("Unknown"):
        print(f"Ship {ship_id} not found in SDE")
        sde_conn.close()
        sys.exit(1)

    print(f"\n{'=' * 70}")
    print(f"{ship_name} (typeID {ship_id})")
    print('=' * 70)

    # Get clusters for this ship
    cur = conn.cursor()

    if args.cluster_id:
        clusters = [(args.cluster_id,)]
    else:
        cur.execute('''
            SELECT DISTINCT cluster_id
            FROM fits
            WHERE ship_id = %s AND cluster_id IS NOT NULL
            ORDER BY cluster_id
        ''', (ship_id,))
        clusters = cur.fetchall()
        clusters = [c[0] for c in clusters]

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sample fits from each cluster
    total_sampled = 0
    for cluster_id in clusters:
        print(f"\n--- Cluster {cluster_id} ---")

        # Get sample fits
        fits = get_fits_from_cluster(conn, ship_id, cluster_id, limit=args.samples)
        print(f"  Sampling {len(fits)} fits")

        for i, fit in enumerate(fits, 1):
            eft_content = format_fit_as_eft(sde_conn, ship_id, fit, ship_name)

            # Write to file
            safe_ship_name = ship_name.lower().replace(' ', '_').replace('/', '-')
            filename = f"{safe_ship_name}_cluster_{cluster_id}_fit_{i:03d}.eft"
            filepath = output_dir / filename

            with open(filepath, 'w') as f:
                f.write(eft_content)

            print(f"  → {filename} ({fit['fit_id']})")
            total_sampled += 1

    sde_conn.close()
    conn.close()

    print(f"\n{'=' * 70}")
    print(f"Total sampled: {total_sampled} fits")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"{'=' * 70}")
    print(f"\nThese are REAL lossmail fits that actual players flew.")
    print(f"Each fit represents a point in the cluster's latent space.")
    print(f"\nNext steps:")
    print(f"1. Review the EFT files for quality")
    print(f"2. Import valid fits into evewire as 'meta' templates")
    print(f"3. Generate skill plans from these fits")


if __name__ == "__main__":
    main()
