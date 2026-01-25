#!/usr/bin/env python3
"""
Verify fits against ESI killmail data.

This script checks that the fittings stored in the database match the
original zkillboard/ESI killmail data they were imported from.

Usage:
    python verify_fits.py                    # Verify 10 random fits
    python verify_fits.py --n 100            # Verify 100 fits
    python verify_fits.py --ship-id 11978    # Verify all Scimitar fits
    python verify_fits.py --killmail 132312806  # Verify specific killmail
"""

import sys
import argparse
import json
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass

import psycopg
import requests


@dataclass
class VerificationResult:
    """Result of verifying a single fit."""
    fit_id: int
    killmail_id: int
    ship_id: int
    ship_name: str
    match: bool
    missing_in_db: Set[int]
    extra_in_db: Set[int]
    flag_mismatches: List[Tuple[int, int, int]]  # (item_id, db_flag, esi_flag)
    error: str = None


def get_sde_name(db_url: str, type_id: int) -> str:
    """Get item type name from SDE."""
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM sde.invtypes WHERE type_id = %s", [type_id])
            row = cur.fetchone()
            return row[0] if row else f"Type {type_id}"


def flag_to_slot_name(flag: int) -> str:
    """Convert ESI flag to slot name."""
    # Slot flag ranges from EVE
    if flag == 5:  # Cargo
        return "Cargo"
    elif flag == 87:  # Drone Bay
        return "DroneBay"
    elif 11 <= flag <= 34:  # High slots
        return f"High{flag - 10}"
    elif 35 <= flag <= 48:  # Med slots
        return f"Med{flag - 34}"
    elif 49 <= flag <= 62:  # Low slots
        return f"Low{flag - 48}"
    elif 92 <= flag <= 93:  # Rigs
        return f"Rig{flag - 91}"
    elif 125 <= flag <= 130:  # Subsystems
        return f"Sub{flag - 124}"
    else:
        return f"Flag{flag}"


def esi_flag_to_db_slot(flag: int) -> Tuple[str, int]:
    """
    Convert ESI flag to (slot_type, slot_index).

    ESI Slot Flag Ranges:
    - Low slots: 11-18
    - Med slots: 19-26
    - High slots: 27-34
    - Rigs: 92-93
    - Subsystems: 125-130
    - Cargo: 5
    - Drone Bay: 87

    Returns: ('high', 'med', 'low', 'rig', 'subsystem', 'cargo', 'drone_bay'), index
    """
    if flag == 5:
        return 'cargo', 0
    elif flag == 87:
        return 'drone_bay', 0
    elif 27 <= flag <= 34:
        return 'high', flag - 27
    elif 19 <= flag <= 26:
        return 'med', flag - 19
    elif 11 <= flag <= 18:
        return 'low', flag - 11
    elif 92 <= flag <= 93:
        return 'rig', flag - 92
    elif 125 <= flag <= 130:
        return 'subsystem', flag - 125
    else:
        return 'other', flag


def verify_fit(db_url: str, fit_id: int) -> VerificationResult:
    """
    Verify a single fit against ESI killmail data.

    Returns VerificationResult with comparison details.
    """
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Get fit data
            cur.execute("""
                SELECT f.id, f.killmail_id, f.ship_id,
                       f.high_slots, f.med_slots, f.low_slots, f.rig_slots, f.subsystem_slots
                FROM fits f
                WHERE f.id = %s
            """, [fit_id])

            row = cur.fetchone()
            if not row:
                return VerificationResult(
                    fit_id=fit_id, killmail_id=0, ship_id=0, ship_name="",
                    match=False, missing_in_db=set(), extra_in_db=set(),
                    flag_mismatches=[], error="Fit not found"
                )

            fit_id, killmail_id, ship_id, high_slots, med_slots, low_slots, rig_slots, subsystem_slots = row
            ship_name = get_sde_name(db_url, ship_id)

            # Build DB items set - all items regardless of position
            # (charges and modules are stored in the same slot arrays)
            db_items = set()
            for slots in [high_slots, med_slots, low_slots, rig_slots, subsystem_slots]:
                if slots:
                    db_items.update(slots)

    # Get killmail hash from zkillboard
    try:
        zkb_response = requests.get(f"https://zkillboard.com/api/killID/{killmail_id}/", timeout=10)
        zkb_response.raise_for_status()
        zkb_data = zkb_response.json()

        if not zkb_data:
            return VerificationResult(
                fit_id=fit_id, killmail_id=killmail_id, ship_id=ship_id, ship_name=ship_name,
                match=False, missing_in_db=set(), extra_in_db=set(),
                flag_mismatches=[], error="No data from zkillboard"
            )

        killmail_hash = zkb_data[0]['zkb']['hash']
    except Exception as e:
        return VerificationResult(
            fit_id=fit_id, killmail_id=killmail_id, ship_id=ship_id, ship_name=ship_name,
            match=False, missing_in_db=set(), extra_in_db=set(),
            flag_mismatches=[], error=f"Failed to get zkillboard data: {e}"
        )

    # Get full killmail from ESI
    try:
        esi_response = requests.get(
            f"https://esi.evetech.net/latest/killmails/{killmail_id}/{killmail_hash}/",
            timeout=10
        )
        esi_response.raise_for_status()
        killmail = esi_response.json()
    except Exception as e:
        return VerificationResult(
            fit_id=fit_id, killmail_id=killmail_id, ship_id=ship_id, ship_name=ship_name,
            match=False, missing_in_db=set(), extra_in_db=set(),
            flag_mismatches=[], error=f"Failed to get ESI data: {e}"
        )

    # Build ESI items set - modules and charges in valid slot ranges
    esi_items = set()
    # Valid slot flags:
    # - Low: 11-18, Med: 19-26, High: 27-34
    # - Rigs: 92-94 (some ships have 3 rig slots)
    # - Subsystems: 125-130
    valid_flags = set(range(11, 35)) | {92, 93, 94} | set(range(125, 131))

    for item in killmail.get('victim', {}).get('items', []):
        flag = item['flag']
        if flag in valid_flags:
            esi_items.add(item['item_type_id'])

    # Compare item sets (not positions)
    missing_in_db = esi_items - db_items
    extra_in_db = db_items - esi_items

    # Determine if match
    match = (len(missing_in_db) == 0 and len(extra_in_db) == 0)

    return VerificationResult(
        fit_id=fit_id,
        killmail_id=killmail_id,
        ship_id=ship_id,
        ship_name=ship_name,
        match=match,
        missing_in_db=missing_in_db,
        extra_in_db=extra_in_db,
        flag_mismatches=[],
    )


def main():
    parser = argparse.ArgumentParser(
        description="Verify fits against ESI killmail data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--n', type=int, default=10, help='Number of fits to verify')
    parser.add_argument('--ship-id', type=int, help='Only verify fits for this ship')
    parser.add_argument('--killmail', type=int, help='Verify specific killmail ID')
    parser.add_argument('--all', action='store_true', help='Verify all fits (slow!)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()

    db_url = "postgresql://genie@/career_research"

    # Get fits to verify
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            if args.killmail:
                cur.execute("""
                    SELECT f.id FROM fits f WHERE f.killmail_id = %s
                """, [args.killmail])
                fit_ids = [row[0] for row in cur.fetchall()]
            elif args.ship_id:
                cur.execute("""
                    SELECT f.id FROM fits f
                    WHERE f.ship_id = %s
                    ORDER BY RANDOM()
                    LIMIT %s
                """, [args.ship_id, args.n])
                fit_ids = [row[0] for row in cur.fetchall()]
            elif args.all:
                cur.execute("SELECT id FROM fits")
                fit_ids = [row[0] for row in cur.fetchall()]
            else:
                cur.execute("""
                    SELECT f.id FROM fits f
                    ORDER BY RANDOM()
                    LIMIT %s
                """, [args.n])
                fit_ids = [row[0] for row in cur.fetchall()]

    print(f"Verifying {len(fit_ids)} fits...\n")

    results = []
    match_count = 0
    error_count = 0

    for i, fit_id in enumerate(fit_ids, 1):
        result = verify_fit(db_url, fit_id)
        results.append(result)

        if result.error:
            error_count += 1
            print(f"[{i}/{len(fit_ids)}] ❌ Fit {result.fit_id}: {result.error}")
        elif result.match:
            match_count += 1
            print(f"[{i}/{len(fit_ids)}] ✅ Fit {result.fit_id}: {result.ship_name} (KM {result.killmail_id})")
        else:
            missing = len(result.missing_in_db)
            extra = len(result.extra_in_db)
            print(f"[{i}/{len(fit_ids)}] ❌ Fit {result.fit_id}: {result.ship_name} (KM {result.killmail_id}) - Missing: {missing}, Extra: {extra}")

            if args.verbose and (result.missing_in_db or result.extra_in_db):
                if result.missing_in_db:
                    for item_id in list(result.missing_in_db)[:5]:
                        item_name = get_sde_name(db_url, item_id)
                        print(f"    Missing: {item_name} ({item_id})")
                    if len(result.missing_in_db) > 5:
                        print(f"    ... and {len(result.missing_in_db) - 5} more")
                if result.extra_in_db:
                    for item_id in list(result.extra_in_db)[:5]:
                        item_name = get_sde_name(db_url, item_id)
                        print(f"    Extra: {item_name} ({item_id})")
                    if len(result.extra_in_db) > 5:
                        print(f"    ... and {len(result.extra_in_db) - 5} more")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"VERIFICATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total verified: {len(results)}")
    print(f"✅ Matches: {match_count} ({100 * match_count / len(results) if results else 0:.1f}%)")
    print(f"❌ Mismatches: {len(results) - match_count - error_count}")
    print(f"⚠️  Errors: {error_count}")

    if match_count == len(results) - error_count:
        print("\n🎉 All verified fits match!")
        return 0
    else:
        print(f"\n⚠️  Found {(len(results) - match_count - error_count)} mismatches")
        return 1


if __name__ == "__main__":
    sys.exit(main())
