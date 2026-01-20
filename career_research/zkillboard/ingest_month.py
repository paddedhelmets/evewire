"""
Ingest a full month of killmail data.

Usage:
    python ingest_month.py 2025 01
    python ingest_month.py 2025 01 --dry-run
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from zkillboard.ingest import KillmailImporter


def ingest_month(year: int, month: int, dry_run: bool = False):
    """Ingest all killmails for a given month."""
    start_date = datetime(year, month, 1)

    # Calculate end date (first day of next month)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    print(f"Ingesting {year:04d}-{month:02d}: {start_date.date()} to {end_date.date()}")

    if dry_run:
        print(f"  Would process {(end_date - start_date).days + 1} days")
        return 0

    importer = KillmailImporter(batch_size=1000)

    try:
        total = importer.import_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        importer.print_stats()
        return total
    except Exception as e:
        print(f"Error ingesting {year}-{month:02d}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a month of killmails")
    parser.add_argument("year", type=int, help="Year (e.g., 2025)")
    parser.add_argument("month", type=int, help="Month (1-12)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be ingested")
    args = parser.parse_args()

    sys.exit(ingest_month(args.year, args.month, args.dry_run))
