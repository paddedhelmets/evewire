#!/usr/bin/env python3
"""
Export representative fits from clusters.

Instead of synthesizing fits by reconciling positions (which creates
invalid fits with duplicate unique modules), this exports the actual
fit closest to the cluster centroid.

Usage:
    python export_representative_fits.py <ship_id> [...ship_ids]
    python export_representative_fits.py --all  # Export all clustered ships
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

# Add evewire to path
evewire_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(evewire_path))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'evewire.settings')
import django
django.setup()

import psycopg
import sqlite3

from core.fitting_formats.eft import EFTSerializer
from core.fitting_formats.base import FittingData


def get_cluster_representative(db_url: str, ship_id: int, cluster_id: int) -> int:
    """
    Find the fit closest to the cluster centroid.

    The cluster centroid is the average vector of all fits in the cluster.
    We find the fit with minimum cosine distance to this centroid.
    """
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Find the fit closest to the cluster centroid
            # We use AVG to compute the centroid, then find the fit with minimum distance to it
            cur.execute("""
                WITH cluster_fits AS (
                    SELECT id, fit_vector
                    FROM fits
                    WHERE ship_id = %s AND cluster_id = %s AND fit_vector IS NOT NULL
                ),
                centroid AS (
                    SELECT AVG(fit_vector)::vector as centroid_vector
                    FROM cluster_fits
                )
                SELECT cf.id
                FROM cluster_fits cf, centroid c
                ORDER BY cf.fit_vector <=> c.centroid_vector
                LIMIT 1
            """, [ship_id, cluster_id])

            row = cur.fetchone()
            if row:
                return row[0]
            return None


def get_fit_data(db_url: str, fit_id: int) -> Dict:
    """Get full fit data including modules and killmail info."""
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    f.id,
                    f.killmail_id,
                    f.ship_id,
                    f.high_slots,
                    f.med_slots,
                    f.low_slots,
                    f.rig_slots,
                    f.subsystem_slots
                FROM fits f
                WHERE f.id = %s
            """, [fit_id])

            row = cur.fetchone()
            if not row:
                return None

            return {
                'id': row[0],
                'killmail_id': row[1],
                'ship_id': row[2],
                'high_slots': row[3],
                'med_slots': row[4],
                'low_slots': row[5],
                'rig_slots': row[6],
                'subsystem_slots': row[7],
            }


def get_cluster_samples(db_url: str, ship_id: int, cluster_id: int, limit: int = 10) -> List[Dict]:
    """Get sample fits from a cluster for provenance."""
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    killmail_id
                FROM fits
                WHERE ship_id = %s AND cluster_id = %s
                ORDER BY RANDOM()
                LIMIT %s
            """, [ship_id, cluster_id, limit])

            return [
                {'id': row[0], 'killmail_id': row[1]}
                for row in cur.fetchall()
            ]


def get_ship_name(sde_conn: sqlite3.Connection, ship_id: int) -> str:
    """Get ship name from SDE."""
    cur = sde_conn.cursor()
    cur.execute('SELECT typeName FROM core_itemtype WHERE typeID = ?', (ship_id,))
    row = cur.fetchone()
    return row[0] if row else f"Ship {ship_id}"


def get_item_name(sde_conn: sqlite3.Connection, type_id: int) -> str:
    """Get item name from SDE."""
    cur = sde_conn.cursor()
    cur.execute('SELECT typeName FROM core_itemtype WHERE typeID = ?', (type_id,))
    row = cur.fetchone()
    return row[0] if row else f"Type {type_id}"


def fit_to_eft(sde_conn: sqlite3.Connection, fit_data: Dict, ship_name: str, cluster_id: int) -> str:
    """Convert fit data to EFT format."""
    # Build FittingData
    data = FittingData(
        name=f"Cluster {cluster_id} Representative",
        ship_type_id=fit_data['ship_id'],
        ship_type_name=ship_name,
        high_slots=fit_data['high_slots'] or [],
        med_slots=fit_data['med_slots'] or [],
        low_slots=fit_data['low_slots'] or [],
        rig_slots=fit_data['rig_slots'] or [],
        subsystem_slots=fit_data['subsystem_slots'] or [],
    )

    serializer = EFTSerializer()
    return serializer.serialize(data)


def format_provenance_markdown(samples: List[Dict]) -> str:
    """Format provenance information as markdown."""
    lines = []
    lines.append("### Cluster Samples")
    lines.append("")
    lines.append("| Fit ID | Killmail ID | Zkillboard |")
    lines.append("|--------|-------------|------------|")

    for sample in samples:
        fit_id = sample['id']
        killmail_id = sample['killmail_id']
        url = f"https://zkillboard.com/kill/{killmail_id}/"
        lines.append(f"| {fit_id} | [{killmail_id}]({url}) | [Link]({url}) |")

    return '\n'.join(lines)


def export_cluster(db_url: str, sde_conn: sqlite3.Connection, ship_id: int,
                   cluster_id: int, output_dir: Path) -> str:
    """Export a single cluster to markdown."""
    ship_name = get_ship_name(sde_conn, ship_id)

    # Get representative fit
    rep_fit_id = get_cluster_representative(db_url, ship_id, cluster_id)
    if not rep_fit_id:
        print(f"  No representative fit for cluster {cluster_id}")
        return None

    # Get fit data
    fit_data = get_fit_data(db_url, rep_fit_id)
    if not fit_data:
        print(f"  Fit {rep_fit_id} not found")
        return None

    # Get cluster stats
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE id = %s) as is_rep
                FROM fits
                WHERE ship_id = %s AND cluster_id = %s
            """, [rep_fit_id, ship_id, cluster_id])
            row = cur.fetchone()
            total_fits = row[0]

    # Get samples
    samples = get_cluster_samples(db_url, ship_id, cluster_id, limit=15)

    # Generate EFT
    eft_content = fit_to_eft(sde_conn, fit_data, ship_name, cluster_id)

    # Build markdown
    md_lines = []
    md_lines.append(f"# {ship_name} - Cluster {cluster_id}")
    md_lines.append("")
    md_lines.append(f"## Representative Fit ({total_fits} fits in cluster)")
    md_lines.append("")
    md_lines.append(f"**Fit ID**: {rep_fit_id}")
    md_lines.append(f"**Killmail**: [{fit_data['killmail_id']}](https://zkillboard.com/kill/{fit_data['killmail_id']}/)")
    md_lines.append("")
    md_lines.append("```")
    md_lines.append(eft_content)
    md_lines.append("```")
    md_lines.append("")

    # Add provenance
    md_lines.append(format_provenance_markdown(samples))
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"*This is the actual fit closest to the cluster centroid.*")
    md_lines.append(f"*It represents the most common configuration in this cluster.*")
    md_lines.append(f"*Cluster {cluster_id} contains {total_fits} similar fits.*")

    # Write file
    filename = f"{ship_name.lower().replace(' ', '_')}_cluster_{cluster_id}_representative.md"
    filepath = output_dir / filename

    with open(filepath, 'w') as f:
        f.write('\n'.join(md_lines))

    return filename


def main():
    parser = argparse.ArgumentParser(
        description='Export representative fits from clusters'
    )
    parser.add_argument('ship_ids', nargs='*', help='Ship typeIDs to process')
    parser.add_argument('--all', action='store_true', help='Export all clustered ships')
    parser.add_argument('--output-dir', type=str, default='output/representative',
                        help='Output directory for markdown files')
    args = parser.parse_args()

    db_url = "postgresql://genie@/career_research"
    sde_path = Path('~/data/evewire/eve_sde.sqlite3').expanduser()

    # Get ship IDs
    if args.all:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ship_id
                    FROM fits
                    WHERE cluster_id IS NOT NULL
                    ORDER BY ship_id
                """)
                ship_ids = [row[0] for row in cur.fetchall()]
    else:
        ship_ids = [int(sid) for sid in args.ship_ids]

    if not ship_ids:
        print("No ships to process")
        return

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Connect to SDE
    sde_conn = sqlite3.connect(sde_path)

    # Create index
    index_lines = ["# Representative Fit Library", ""]
    index_lines.append(f"*Generated from {len(ship_ids)} ships*")
    index_lines.append("")
    index_lines.append("Each file contains the actual fit closest to the cluster centroid.")
    index_lines.append("")
    index_lines.append("## Ships")
    index_lines.append("")

    # Process each ship
    for ship_id in ship_ids:
        ship_name = get_ship_name(sde_conn, ship_id)
        print(f"\n{'=' * 70}")
        print(f"Processing: {ship_name} (typeID {ship_id})")
        print('=' * 70)

        # Get clusters
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT cluster_id
                    FROM fits
                    WHERE ship_id = %s AND cluster_id IS NOT NULL
                    ORDER BY cluster_id
                """, [ship_id])
                clusters = [row[0] for row in cur.fetchall()]

        # Export each cluster
        for cluster_id in clusters:
            print(f"  Cluster {cluster_id}...")
            filename = export_cluster(db_url, sde_conn, ship_id, cluster_id, output_dir)
            if filename:
                index_lines.append(f"- [{ship_name}]({filename}) - Cluster {cluster_id}")

    sde_conn.close()

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
