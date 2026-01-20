#!/usr/bin/env python3
"""
Analyze clusters for a specific ship.

Usage:
    python analyze_ship.py <ship_id>
    python analyze_ship.py 12005    # Ishtar
    python analyze_ship.py 626      # Vexor
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from clustering.analyze import ClusterAnalyzer
from clustering.cluster import FitClusterer


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_ship.py <ship_id>")
        sys.exit(1)

    ship_id = int(sys.argv[1])

    analyzer = ClusterAnalyzer()
    ship_name = analyzer.get_ship_name(ship_id)

    print(f"\n{'=' * 70}")
    print(f"{ship_name} (typeID {ship_id})")
    print('=' * 70)

    # Cluster the ship
    clusterer = FitClusterer(n_clusters=5)
    clusterer.cluster_ship(ship_id)

    # Get canonical fits
    canonical_fits = analyzer.analyze_ship_clusters(ship_id, limit=10)

    print(f"\nFound {len(canonical_fits)} clusters:\n")

    for i, canonical in enumerate(canonical_fits, 1):
        print(f"{'=' * 70}")
        print(f"Cluster {i}: {canonical.fit_count} fits")
        print('=' * 70)
        print(canonical.format())
        print()


if __name__ == "__main__":
    main()
