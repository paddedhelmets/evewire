#!/usr/bin/env python3
"""
Show popular ships with embeddings.

Usage:
    python popular_ships.py [--limit N]
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from clustering.analyze import ClusterAnalyzer


def main():
    parser = argparse.ArgumentParser(description="Show popular ships with embeddings")
    parser.add_argument("--limit", type=int, default=20, help="Number of ships to show")
    args = parser.parse_args()

    analyzer = ClusterAnalyzer()

    print(f"\nTop {args.limit} Ships (by embeddings)")
    print("=" * 70)

    popular = analyzer.find_popular_ships(limit=args.limit)

    for i, (ship_id, ship_name, count) in enumerate(popular, 1):
        pct = 100 * count / 5952309  # Total fits
        print(f"{i:2}. {ship_name:<30} {count:>7} ({pct:.2f}%)")

    print()


if __name__ == "__main__":
    main()
