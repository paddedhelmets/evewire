#!/usr/bin/env python3
"""
Batch cluster all ships in the database.

This script clusters fits for all ships that haven't been clustered yet.
It handles progress tracking, error recovery, and progress monitoring.

Ships SKIPPED by default (queried from SDE):
- Capsules (group 29)
- Shuttles (group 31)
- Corvettes/rookie ships (group 237)
- All anchored or anchorable structures
- All deployables, starbases, structures, orbitals, fighters (by category)

Usage:
    python cluster_all_ships.py                    # Cluster all unclustered ships
    python cluster_all_ships.py --ship-id 626      # Cluster specific ship
    python cluster_all_ships.py --min-fits 100     # Only ships with 100+ fits
    python cluster_all_ships.py --include-trivial  # Include capsules/shuttles/corvettes/structures
    python cluster_all_ships.py --clear-all        # Clear existing clusters and re-run

Progress is tracked in the database - you can Ctrl+C and resume.
"""

import sys
import argparse
import signal
from pathlib import Path
from typing import List, Set, Optional
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from clustering.cluster import FitClusterer


# Ship groups to skip (not real ships - queried from SDE)
# These are populated dynamically from the SDE on startup
SKIP_GROUP_IDS = set()

# Capital ship groups to exclude (endgame content, beyond scope)
CAPITAL_GROUP_IDS = {
    30,    # Titan
    485,   # Dreadnought
    513,   # Freighter
    547,   # Carrier
    659,   # Supercarrier
    902,   # Jump Freighter
    1022,  # Prototype Exploration Ship (Zorya)
    1538,  # Force Auxiliary
    4594,  # Lancer Dreadnought (new triglavian dread)
}

# Specific type IDs to skip (if needed, for things not in SDE groups)
SKIP_TYPE_IDS = set()


def load_skip_groups_from_sde(db_url: str) -> None:
    """
    Load groups to skip from the SDE.

    This includes:
    - Capsules (group 29)
    - Shuttles (group 31)
    - Corvettes/rookie ships (group 237)
    - All anchored or anchorable structures (starbases, depots, etc.)
    - All deployables, starbases, structures, orbitals (by category)
    - All fighters (6 groups - they're ammo/carrier drones, not real ships)
    - Capital ships (endgame content, beyond provisioning scope)
    """
    global SKIP_GROUP_IDS

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # First check if SDE is loaded
            cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'sde' AND table_name = 'invgroups')")
            if not cur.fetchone()[0]:
                print("Warning: SDE not loaded in database. Using hardcoded skip groups.")
                SKIP_GROUP_IDS = {29, 31, 237}  # Fallback to hardcoded groups
                return

            # Query SDE for groups to skip
            # 1. Specific groups we know to skip
            # 2. Groups that are anchored or anchorable
            # 3. Groups in categories that are structures/deployables/fighters/drones
            cur.execute("""
                SELECT DISTINCT g.group_id
                FROM sde.invgroups g
                JOIN sde.invcategories c ON c.category_id = g.category_id
                WHERE g.group_id IN (29, 31, 237)  -- Capsule, Shuttle, Corvette
                   OR g.anchored = TRUE
                   OR g.anchorable = TRUE
                   OR c.name IN ('Deployable', 'Starbase', 'Structure', 'Orbitals', 'Fighter', 'Drone')
            """)

            SKIP_GROUP_IDS = {row[0] for row in cur.fetchall()}

            # Add capital ship groups (endgame, beyond scope)
            SKIP_GROUP_IDS.update(CAPITAL_GROUP_IDS)

    print(f"Loaded {len(SKIP_GROUP_IDS)} groups to skip from SDE (including {len(CAPITAL_GROUP_IDS)} capital groups)")


# Shutdown flag for graceful Ctrl+C
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    shutdown_requested = True
    print("\n\nShutdown requested. Finishing current ship and exiting...")


signal.signal(signal.SIGINT, signal_handler)


def get_ships_needing_clustering(
    db_url: str,
    min_fits: int = 10,
    skip_group_ids: Optional[Set[int]] = None,
    skip_type_ids: Optional[Set[int]] = None,
) -> List[tuple[int, int, str]]:
    """
    Get ships that need clustering.

    Returns list of (ship_id, fit_count, ship_name) tuples.
    """
    skip_groups = skip_group_ids or SKIP_GROUP_IDS
    skip_types = skip_type_ids or SKIP_TYPE_IDS

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Check if SDE is available in postgres
            cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'sde' AND table_name = 'invtypes')")
            sde_available = cur.fetchone()[0]

            if sde_available:
                # Use SDE join to get ship names directly
                skip_list = list(skip_groups) if skip_groups else []
                skip_placeholder = ', '.join(['%s'] * len(skip_list)) if skip_list else 'NULL'
                skip_clause = f"AND t.group_id NOT IN ({skip_placeholder})" if skip_list else ""

                # Also skip specific type IDs
                type_skip_list = list(skip_types) if skip_types else []
                type_skip_placeholder = ', '.join(['%s'] * len(type_skip_list)) if type_skip_list else 'NULL'
                type_skip_clause = f"AND f.ship_id NOT IN ({type_skip_placeholder})" if type_skip_list else ""

                query = f"""
                    SELECT
                        f.ship_id,
                        t.name as ship_name,
                        COUNT(*) as fit_count,
                        COUNT(*) FILTER (WHERE f.cluster_id IS NULL) as unclustered
                    FROM fits f
                    JOIN sde.invtypes t ON t.type_id = f.ship_id
                    WHERE t.published = TRUE
                        {skip_clause}
                        {type_skip_clause}
                    GROUP BY f.ship_id, t.name
                    HAVING COUNT(*) FILTER (WHERE f.cluster_id IS NULL) >= %s
                    ORDER BY unclustered DESC
                """

                params = skip_list + type_skip_list + [min_fits]
                cur.execute(query, params)

                ships = [(row[0], row[2], row[1]) for row in cur.fetchall()]

            else:
                # Fallback to old method without SDE
                skip_list = list(skip_groups) if skip_groups else []
                skip_placeholder = ', '.join(['%s'] * len(skip_list)) if skip_list else 'NULL'
                skip_clause = f"AND f.ship_id NOT IN ({skip_placeholder})" if skip_list else ""

                query = f"""
                    SELECT
                        f.ship_id,
                        COUNT(*) as fit_count,
                        COUNT(*) FILTER (WHERE f.cluster_id IS NULL) as unclustered
                    FROM fits f
                    WHERE 1=1
                        {skip_clause}
                    GROUP BY f.ship_id
                    HAVING COUNT(*) FILTER (WHERE f.cluster_id IS NULL) >= %s
                    ORDER BY unclustered DESC
                """

                params = skip_list + [min_fits]
                cur.execute(query, params)

                # Try to get ship names from sqlite SDE
                ships = []
                sde_path = Path('~/data/evewire/eve_sde.sqlite3').expanduser()

                try:
                    import sqlite3
                    sde_conn = sqlite3.connect(sde_path)

                    for ship_id, fit_count, unclustered in cur.fetchall():
                        # Get ship name from SDE
                        sde_cur = sde_conn.cursor()
                        sde_cur.execute('SELECT typeName FROM core_itemtype WHERE typeID = ?', (ship_id,))
                        row = sde_cur.fetchone()
                        ship_name = row[0] if row else f"Ship {ship_id}"

                        ships.append((ship_id, unclustered, ship_name))

                    sde_conn.close()

                except Exception as e:
                    print(f"Warning: Could not load ship names from SDE: {e}")
                    for ship_id, fit_count, unclustered in cur.fetchall():
                        ships.append((ship_id, unclustered, f"Ship {ship_id}"))

    return ships


def clear_all_clusters(db_url: str) -> None:
    """Clear all existing cluster assignments."""
    print("WARNING: This will clear all existing cluster assignments!")
    response = input("Are you sure? Type 'yes' to continue: ")

    if response.lower() != 'yes':
        print("Aborted.")
        return

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE fits SET cluster_id = NULL")
            affected = cur.rowcount
            conn.commit()

    print(f"Cleared cluster_id from {affected} fits")


def cluster_ship(
    ship_id: int,
    ship_name: str,
    clusterer: FitClusterer,
    n_clusters: int = 5,
) -> bool:
    """
    Cluster a single ship.

    Returns True if successful, False on error.
    """
    try:
        results = clusterer.cluster_ship(ship_id)
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Batch cluster all ships in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--ship-id',
        type=int,
        help='Cluster a specific ship (by typeID)',
    )
    parser.add_argument(
        '--min-fits',
        type=int,
        default=10,
        help='Minimum fit count to cluster a ship (default: 10)',
    )
    parser.add_argument(
        '--n-clusters',
        type=int,
        default=5,
        help='Number of clusters per ship (default: 5)',
    )
    parser.add_argument(
        '--clear-all',
        action='store_true',
        help='Clear existing clusters and re-run everything',
    )
    parser.add_argument(
        '--include-trivial',
        action='store_true',
        help='Include capsules, shuttles, corvettes, and structures (normally skipped)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be clustered without doing it',
    )
    args = parser.parse_args()

    db_url = "postgresql://genie@/career_research"

    # Load skip groups from SDE
    if not args.include_trivial:
        load_skip_groups_from_sde(db_url)

    from clustering.cluster import FitClusterer
    clusterer = FitClusterer(db_url=db_url, n_clusters=args.n_clusters)

    # Clear all clusters if requested
    if args.clear_all:
        clear_all_clusters(db_url)
        return

    # Single ship mode
    if args.ship_id:
        print(f"\nClustering ship {args.ship_id}...")
        cluster_ship(args.ship_id, f"Ship {args.ship_id}", clusterer, args.n_clusters)
        print("Done!")
        return

    # Get ships needing clustering
    print("Finding ships needing clustering...")
    ships = get_ships_needing_clustering(
        db_url,
        min_fits=args.min_fits,
    )

    if not ships:
        print("All ships are already clustered!")
        return

    print(f"\nFound {len(ships)} ships needing clustering:\n")

    total_fits = sum(fit_count for _, fit_count, _ in ships)
    print(f"Total fits to cluster: {total_fits:,}")
    print(f"Ships to process: {len(ships)}")

    if args.dry_run:
        print("\nDry run - would cluster:")
        for ship_id, fit_count, ship_name in ships[:20]:
            print(f"  {ship_name} ({ship_id}): {fit_count:,} fits")
        if len(ships) > 20:
            print(f"  ... and {len(ships) - 20} more")
        return

    # Confirm
    response = input("\nProceed? [Y/n]: ")
    if response.lower() == 'n':
        print("Aborted.")
        return

    # Cluster all ships
    print("\n" + "=" * 70)
    print("CLUSTERING STARTED")
    print("=" * 70 + "\n")

    start_time = time.time()
    success_count = 0
    error_count = 0

    for i, (ship_id, fit_count, ship_name) in enumerate(ships, 1):
        if shutdown_requested:
            print("\nShutdown requested. Exiting gracefully...")
            break

        print(f"[{i}/{len(ships)}] {ship_name} ({ship_id}) - {fit_count:,} fits")

        if cluster_ship(ship_id, ship_name, clusterer, args.n_clusters):
            success_count += 1
        else:
            error_count += 1

        # Progress ETA
        if i > 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = len(ships) - i
            eta = avg_time * remaining

            print(f"  Progress: {i}/{len(ships)} | Errors: {error_count} | ETA: {eta/60:.1f} min")

    # Summary
    print("\n" + "=" * 70)
    print("CLUSTERING COMPLETE")
    print("=" * 70)
    print(f"Successfully clustered: {success_count} ships")
    print(f"Errors: {error_count} ships")
    print(f"Total time: {(time.time() - start_time) / 60:.1f} minutes")
    print()


if __name__ == "__main__":
    main()
