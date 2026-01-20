#!/usr/bin/env python3
"""
Generate all fit embeddings.

Run this to populate fit_vector for all fits in the database.
This will take several hours for the full dataset.

Usage:
    python generate_embeddings.py [--limit N]
"""

import sys
import argparse
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from clustering.embeddings import FitEmbedder


def main():
    parser = argparse.ArgumentParser(description="Generate fit embeddings")
    parser.add_argument("--limit", type=int, help="Limit number of fits to process")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for DB updates")
    args = parser.parse_args()

    embedder = FitEmbedder()

    print(f"Generating embeddings for all fits (limit={args.limit or 'none'})...")
    count = embedder.generate_embeddings_batch(limit=args.limit, batch_size=args.batch_size)
    print(f"Done! Generated {count} embeddings.")


if __name__ == "__main__":
    main()
