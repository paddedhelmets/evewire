#!/usr/bin/env python3
"""
Reconcile cluster fits to find exact matches and provenance.

This samples multiple lossmails from a cluster, reconciles them slot-by-slot,
and only outputs fits that have consensus. Includes zkillboard links for verification.

Usage:
    python reconcile_cluster_fits.py <ship_id> [--samples N] [--output-dir OUTPUT]
    python reconcile_cluster_fits.py 12005 --samples 5
    python reconcile_cluster_fits.py 11978 --samples 10

Output:
    Creates Markdown file with reconciled fits and zkillboard links, like:
    ishtar_cluster_2_reconciled.md
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set, Optional
import argparse
from collections import Counter, defaultdict

# Add evewire to path
evewire_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(evewire_path))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'evewire.settings')
import django
django.setup()

import psycopg

from core.fitting_formats.base import FittingData

# EVE Slot Flags - from utils.py
SLOT_FLAGS = {
    'low': list(range(11, 19)),      # LoSlot0-7 (flags 11-18)
    'med': list(range(19, 27)),      # MedSlot0-7 (flags 19-26)
    'high': list(range(27, 35)),     # HiSlot0-7 (flags 27-34)
    'rig': list(range(92, 95)) + [266],  # RigSlot0-3
    'subsystem': list(range(125, 129)),  # SubSystem0-4
}


def get_charge_typeids(sde_conn) -> Set[int]:
    """
    Load all charge typeIDs from SDE using group IDs.

    Charges are items in specific groups that are NOT fitted modules.
    This includes ammunition, missiles, charges, probes, scripts, cap booster charges, etc.
    """
    cur = sde_conn.cursor()

    # Charge group IDs from invGroups
    # These are groups that contain charges/ammo/probes/scripts/etc. (NOT modules)
    charge_groups = (
        # Missile & Rocket Charges
        88, 166, 256, 384, 385, 386, 387, 394, 395, 396, 476, 648, 653, 654, 655, 656, 657, 772,
        # Turret Ammo (Projectile, Hybrid, Laser)
        85, 86,
        # Frequency Crystals
        334, 482, 727,
        # Cap Booster Charges
        87, 4061, 4062,  # 4061 = ElectroPunch, 4062 = BlastShot
        # Probes
        25, 26, 43, 48, 49, 479, 492, 526, 548, 683, 817, 972, 1153, 1160, 1568, 4088,
        # Scripts
        907, 908, 909, 910, 911, 912, 913, 914, 1400, 1549, 1551, 1559, 1569, 1613, 1614,
        1629, 1639, 1701, 1702, 1707, 1708, 1709, 1717,
        # Structure Charges
        1545, 1546, 1547,
        # Standup Charges
        774, 779, 787,
        # Cap Battery/Power Charges
        61, 72, 1769, 1770, 1771, 1772, 1773, 1774, 1810,
        # Nanite Repair Paste
        926,
    )

    # Query for all items in charge groups
    placeholders = ','.join('?' * len(charge_groups))
    cur.execute(f'''
        SELECT DISTINCT it.id
        FROM core_itemtype it
        WHERE it.group_id IN ({placeholders})
    ''', charge_groups)

    charge_typeids = {row[0] for row in cur.fetchall()}

    return charge_typeids


_CHARGE_TYPEID_SET: Optional[Set[int]] = None


def is_module(type_id: int, sde_conn) -> bool:
    """
    Check if a typeID is a fitted module (not a charge).
    Filters out charges by checking if the typeID is in the charge set.
    """
    global _CHARGE_TYPEID_SET
    if _CHARGE_TYPEID_SET is None:
        _CHARGE_TYPEID_SET = get_charge_typeids(sde_conn)

    # Modules are NOT in the charge typeID set
    return type_id not in _CHARGE_TYPEID_SET


def get_fits_from_cluster(conn, ship_id: int, cluster_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Sample actual fits from a cluster."""
    cur = conn.cursor()

    # Get fits with slot arrays
    cur.execute('''
        SELECT id, killmail_id, high_slots, med_slots, low_slots, rig_slots, subsystem_slots
        FROM fits
        WHERE ship_id = %s AND cluster_id = %s
        ORDER BY RANDOM()
        LIMIT %s
    ''', (ship_id, cluster_id, limit))

    fits = []
    for row in cur.fetchall():
        fit_id, killmail_id, high, med, low, rig, subsystem = row
        fits.append({
            'fit_id': fit_id,
            'ship_id': ship_id,
            'cluster_id': cluster_id,
            'killmail_id': killmail_id,
            'zkillboard_url': f"https://zkillboard.com/kill/{killmail_id}/",
            'high_slots': high if high else [],
            'med_slots': med if med else [],
            'low_slots': low if low else [],
            'rig_slots': rig if rig else [],
            'subsystem_slots': subsystem if subsystem else [],
        })

    return fits


def reconcile_by_position(sde_conn, fits: List[Dict[str, Any]]) -> Tuple[FittingData, List[str]]:
    """
    Reconcile fits by slot array position.
    Since zkillboard returns items in flag order, array position ~= slot position.
    """
    # Collect modules by array position across all fits
    slot_positions = {
        'high': defaultdict(Counter),
        'med': defaultdict(Counter),
        'low': defaultdict(Counter),
        'rig': defaultdict(Counter),
        'subsystem': defaultdict(Counter),
    }

    # Track which positions are used in how many fits
    slot_usage = {
        'high': Counter(),
        'med': Counter(),
        'low': Counter(),
        'rig': Counter(),
        'subsystem': Counter(),
    }

    for fit in fits:
        for slot_type in ['high', 'med', 'low', 'rig', 'subsystem']:
            slot_array = fit.get(f'{slot_type}_slots', [])
            # Filter to only modules (no charges)
            modules = [m for m in slot_array if m and is_module(m, sde_conn)]

            for pos, module_id in enumerate(modules):
                slot_positions[slot_type][pos][module_id] += 1
                slot_usage[slot_type][pos] += 1

    # Build consensus: for each position, take most common module
    # Include if at least 40% of fits have something there
    differences = []
    high_slots = []
    med_slots = []
    low_slots = []
    rig_slots = []
    subsystem_slots = []

    threshold = max(1, len(fits) * 0.4)  # At least 1 or 40% of fits

    for slot_type, positions in slot_positions.items():
        max_pos = max(positions.keys()) if positions else 0
        slot_list = []

        for pos in range(max_pos + 1):
            if pos in positions:
                counter = positions[pos]
                usage_count = slot_usage[slot_type][pos]

                if counter:
                    most_common = counter.most_common(1)[0]
                    module_id, count = most_common

                    # Include if enough fits use this slot
                    if usage_count >= threshold:
                        slot_list.append(module_id)

                        # Track differences
                        if len(counter) > 1 or count < len(fits):
                            alternatives = [f"{mid}({c})" for mid, c in counter.most_common(3)]
                            differences.append(
                                f"{slot_type.upper()} pos {pos}: {module_id} ({count}/{len(fits)} fits, "
                                f"{usage_count}/{len(fits)} have module here) "
                                f"alternatives: {', '.join(alternatives)}"
                            )
                    # Else: skip this position (don't add empty slots)
                # Else: position not used in any fit, skip it

        if slot_type == 'high':
            high_slots = slot_list
        elif slot_type == 'med':
            med_slots = slot_list
        elif slot_type == 'low':
            low_slots = slot_list
        elif slot_type == 'rig':
            rig_slots = slot_list
        elif slot_type == 'subsystem':
            subsystem_slots = slot_list

    # Get ship name
    ship_id = fits[0]['ship_id']
    cur = sde_conn.cursor()
    cur.execute('SELECT name FROM core_itemtype WHERE id = ?', (ship_id,))
    row = cur.fetchone()
    ship_name = row[0] if row else f"Ship {ship_id}"
    cluster_id = fits[0]['cluster_id']

    data = FittingData(
        name=f"Cluster {cluster_id} Consensus",
        ship_type_id=ship_id,
        ship_type_name=ship_name,
        high_slots=high_slots,
        med_slots=med_slots,
        low_slots=low_slots,
        rig_slots=rig_slots,
        subsystem_slots=subsystem_slots,
    )

    return data, differences


def format_provenance_markdown(fits: List[Dict[str, Any]]) -> str:
    """Format provenance information as markdown."""
    lines = []
    lines.append("### Sampled Lossmails")
    lines.append("")
    lines.append("| Fit ID | Killmail ID | Zkillboard |")
    lines.append("|--------|-------------|------------|")

    for fit in fits:
        fit_id = fit['fit_id']
        killmail_id = fit['killmail_id']
        url = fit['zkillboard_url']
        lines.append(f"| {fit_id} | [{killmail_id}]({url}) | [Link]({url}) |")

    return '\n'.join(lines)


def reconcile_ship_cluster(conn, sde_conn, ship_id: int, cluster_id: int,
                          num_samples: int, output_dir: Path) -> Optional[str]:
    """Reconcile a single ship cluster and write output."""
    # Get ship name
    cur = sde_conn.cursor()
    cur.execute('SELECT name FROM core_itemtype WHERE id = ?', (ship_id,))
    row = cur.fetchone()
    if not row:
        return None
    ship_name = row[0]

    # Sample fits from cluster
    fits = get_fits_from_cluster(conn, ship_id, cluster_id, limit=num_samples)

    if not fits:
        print(f"  No fits found for cluster {cluster_id}")
        return None

    # Reconcile slots
    fitting_data, differences = reconcile_by_position(sde_conn, fits)

    # Format EFT
    from core.fitting_formats.eft import EFTSerializer
    serializer = EFTSerializer()
    eft_content = serializer.serialize(fitting_data)

    # Create markdown output
    md_lines = []
    md_lines.append(f"# {ship_name} - Cluster {cluster_id}")
    md_lines.append("")
    md_lines.append(f"## Reconciled Fit ({len(fits)} lossmails sampled)")
    md_lines.append("")
    md_lines.append("```")
    md_lines.append(eft_content)
    md_lines.append("```")
    md_lines.append("")

    if differences:
        md_lines.append("### Slot Variations")
        md_lines.append("")
        md_lines.append("The following slots had variation across fits:")
        md_lines.append("")
        for diff in differences:
            md_lines.append(f"- {diff}")
        md_lines.append("")

    md_lines.append(format_provenance_markdown(fits))
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"*Cluster {cluster_id} represents sampled fits from latent space.*")
    md_lines.append(f"*This reconciled fit shows the most common modules for each slot.*")
    md_lines.append(f"*See sampled lossmails below for verification.*")

    filename = f"{ship_name.lower().replace(' ', '_')}_cluster_{cluster_id}_reconciled.md"
    filepath = output_dir / filename

    with open(filepath, 'w') as f:
        f.write('\n'.join(md_lines))

    return filename


def main():
    parser = argparse.ArgumentParser(
        description='Reconcile cluster fits to find exact matches with provenance'
    )
    parser.add_argument('ship_ids', nargs='+', help='Ship typeIDs to process')
    parser.add_argument('--samples', type=int, default=5,
                        help='Samples per cluster (default: 5)')
    parser.add_argument('--output-dir', type=str, default='output/reconciled',
                        help='Output directory for markdown files')
    args = parser.parse_args()

    # Connect to databases
    conn = psycopg.connect('postgresql://genie@/career_research')
    sde_path = Path('~/data/evewire/eve_sde.sqlite3').expanduser()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create index markdown
    index_lines = ["# Meta Fit Library - Reconciled Clusters", ""]
    index_lines.append(f"*Generated from {len(args.ship_ids)} ships*")
    index_lines.append(f"*{args.samples} samples per cluster*")
    index_lines.append("")
    index_lines.append("## Ships")
    index_lines.append("")

    # Process each ship
    import sqlite3
    sde_conn = sqlite3.connect(sde_path)

    for ship_id in args.ship_ids:
        ship_id = int(ship_id)

        # Get ship name
        cur = sde_conn.cursor()
        cur.execute('SELECT name FROM core_itemtype WHERE id = ?', (ship_id,))
        row = cur.fetchone()
        if not row:
            print(f"Ship {ship_id} not found in SDE, skipping...")
            continue

        ship_name = row[0]
        print(f"\n{'=' * 70}")
        print(f"Processing: {ship_name} (typeID {ship_id})")
        print('=' * 70)

        # Get clusters for this ship
        cur = conn.cursor()
        cur.execute('''
            SELECT DISTINCT cluster_id
            FROM fits
            WHERE ship_id = %s AND cluster_id IS NOT NULL
            ORDER BY cluster_id
        ''', (ship_id,))
        clusters = [c[0] for c in cur.fetchall()]

        # Process each cluster
        for cluster_id in clusters:
            print(f"  Cluster {cluster_id}...")
            filename = reconcile_ship_cluster(conn, sde_conn, ship_id, cluster_id, args.samples, output_dir)
            if filename:
                index_lines.append(f"- [{ship_name}]({filename}) - Cluster {cluster_id}")

    sde_conn.close()
    conn.close()

    # Write index
    index_filepath = output_dir / 'index.md'
    with open(index_filepath, 'w') as f:
        f.write('\n'.join(index_lines))

    print(f"\n{'=' * 70}")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Index: {index_filepath.absolute()}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
