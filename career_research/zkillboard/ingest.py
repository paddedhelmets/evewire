"""
Killmail Ingestion Module

Downloads and processes EVE Online killmail dumps from EvereF.

EVE Slot Flags (fitted modules only):
- High slots: 27-34
- Med slots: 19-26
- Low slots: 11-18
- Rig slots: 92-95
- Subsystem slots: 125-129
- Drone bay: 155-159 (ignore for now)
- Cargo: Various (ignore)

Data: https://data.everef.net/killmails/
"""

import tarfile
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Iterator
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime
import tempfile
import os

import requests
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# EVE Fitting Slot Flags (fitted modules only)
# See: https://wiki.eveuniversity.org/Fitting_flags
@dataclass
class SlotFlag:
    """EVE fitting slot flag ranges."""
    HIGH: Tuple[int, int] = (27, 34)      # High power slots
    MED: Tuple[int, int] = (19, 26)       # Medium slots
    LOW: Tuple[int, int] = (11, 18)       # Low power slots
    RIG: Tuple[int, int] = (92, 95)       # Rig slots
    SUBSYSTEM: Tuple[int, int] = (125, 129)  # T3 subsystems

    @classmethod
    def in_range(cls, flag: int, slot_range: Tuple[int, int]) -> bool:
        return slot_range[0] <= flag <= slot_range[1]

    @classmethod
    def get_slot_type(cls, flag: int) -> Optional[str]:
        """Return slot type ('high', 'med', 'low', 'rig', 'subsystem') for a flag."""
        if cls.in_range(flag, cls.HIGH):
            return 'high'
        elif cls.in_range(flag, cls.MED):
            return 'med'
        elif cls.in_range(flag, cls.LOW):
            return 'low'
        elif cls.in_range(flag, cls.RIG):
            return 'rig'
        elif cls.in_range(flag, cls.SUBSYSTEM):
            return 'subsystem'
        return None


@dataclass
class VictimFit:
    """Extracted victim fit from a killmail."""
    killmail_id: int
    killmail_hash: str
    killmail_time: datetime
    solar_system_id: int

    # Victim info
    victim_character_id: Optional[int]
    victim_corporation_id: Optional[int]
    victim_alliance_id: Optional[int]
    ship_id: int

    # Fitted modules by slot (typeIDs)
    high_slots: List[int] = field(default_factory=list)
    med_slots: List[int] = field(default_factory=list)
    low_slots: List[int] = field(default_factory=list)
    rig_slots: List[int] = field(default_factory=list)
    subsystem_slots: List[int] = field(default_factory=list)

    # Additional metadata
    is_npc: bool = False  # True if killed by NPCs
    region_id: Optional[int] = None  # Can be looked up from solar_system_id

    @classmethod
    def from_killmail(cls, data: dict) -> 'VictimFit':
        """Extract victim fit from a killmail JSON."""
        victim = data['victim']
        items = victim.get('items', [])

        # Determine if NPC kill (no character_id in attackers)
        is_npc = all(a.get('character_id') is None for a in data.get('attackers', []))

        fit = cls(
            killmail_id=data['killmail_id'],
            killmail_hash=data['killmail_hash'],
            killmail_time=datetime.fromisoformat(data['killmail_time'].replace('Z', '+00:00')),
            solar_system_id=data['solar_system_id'],
            victim_character_id=victim.get('character_id'),
            victim_corporation_id=victim.get('corporation_id'),
            victim_alliance_id=victim.get('alliance_id'),
            ship_id=victim['ship_type_id'],
            is_npc=is_npc,
        )

        # Extract fitted modules (singleton=0 means fitted, not cargo/implant)
        for item in items:
            # Skip cargo, drone bay, etc. (singleton > 0 or not in fitting slots)
            if item.get('singleton', 0) != 0:
                continue

            flag = item['flag']
            item_type_id = item['item_type_id']

            slot_type = SlotFlag.get_slot_type(flag)
            if slot_type == 'high':
                fit.high_slots.append(item_type_id)
            elif slot_type == 'med':
                fit.med_slots.append(item_type_id)
            elif slot_type == 'low':
                fit.low_slots.append(item_type_id)
            elif slot_type == 'rig':
                fit.rig_slots.append(item_type_id)
            elif slot_type == 'subsystem':
                fit.subsystem_slots.append(item_type_id)

        return fit

    def to_sql_values(self) -> dict:
        """Convert to SQL parameter dict."""
        return {
            'killmail_id': self.killmail_id,
            'killmail_hash': self.killmail_hash,
            'killmail_time': self.killmail_time,
            'solar_system_id': self.solar_system_id,
            'victim_character_id': self.victim_character_id,
            'victim_corporation_id': self.victim_corporation_id,
            'victim_alliance_id': self.victim_alliance_id,
            'victim_ship_id': self.ship_id,
            'is_npc': self.is_npc,
            'ship_id': self.ship_id,
            'high_slots': self.high_slots,
            'med_slots': self.med_slots,
            'low_slots': self.low_slots,
            'rig_slots': self.rig_slots,
            'subsystem_slots': self.subsystem_slots,
            'killed_at': self.killmail_time,
        }


class KillmailImporter:
    """
    Import killmail data from EvereF dumps into PostgreSQL.

    Usage:
        importer = KillmailImporter(db_url="postgresql://genie@/career_research")
        importer.import_date('2025-01-01')
        importer.import_range('2025-01-01', '2025-01-31')
    """

    BASE_URL = "https://data.everef.net/killmails/"

    def __init__(
        self,
        db_url: str = "postgresql://genie@/career_research",
        data_dir: Optional[Path] = None,
        batch_size: int = 1000,
    ):
        """
        Initialize the importer.

        Args:
            db_url: PostgreSQL connection URL
            data_dir: Directory to cache downloaded files (default: temp dir)
            batch_size: Number of fits to insert per batch
        """
        self.db_url = db_url
        self.data_dir = data_dir or Path(tempfile.gettempdir()) / "killmails"
        self.batch_size = batch_size
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Stats tracking
        self.stats = {
            'files_processed': 0,
            'killmails_seen': 0,
            'fits_extracted': 0,
            'fits_imported': 0,
            'duplicates_skipped': 0,
        }

    def _get_conn(self):
        """Get a database connection."""
        return psycopg.connect(self.db_url)

    def _download_file(self, date_str: str, dest: Path) -> Path:
        """
        Download a killmail dump file for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format
            dest: Destination directory

        Returns:
            Path to downloaded file
        """
        filename = f"killmails-{date_str}.tar.bz2"
        url = urljoin(self.BASE_URL, f"{date_str[:4]}/{filename}")
        dest_path = dest / filename

        if dest_path.exists():
            logger.info(f"File already exists: {dest_path}")
            return dest_path

        logger.info(f"Downloading {url}...")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        logger.info(f"Downloaded to {dest_path}")
        return dest_path

    def _parse_tar_bz2(self, archive_path: Path) -> Iterator[dict]:
        """
        Parse killmails from a tar.bz2 archive.

        Yields:
            Killmail JSON dictionaries
        """
        with tarfile.open(archive_path, 'r:bz2') as tar:
            for member in tar:
                if not member.isfile():
                    continue

                # Skip directory entries
                if member.name.endswith('/'):
                    continue

                try:
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    data = json.load(f)
                    self.stats['killmails_seen'] += 1
                    yield data
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse {member.name}: {e}")
                except Exception as e:
                    logger.warning(f"Error processing {member.name}: {e}")

    def _insert_batch(self, conn, fits: List[VictimFit]) -> int:
        """
        Insert a batch of fits into the database.

        Returns:
            Number of fits actually inserted (excluding duplicates)
        """
        if not fits:
            return 0

        inserted = 0

        with conn.cursor() as cur:
            for fit in fits:
                params = fit.to_sql_values()
                try:
                    # Insert killmail metadata (ignore if exists)
                    # Need to handle both killmail_id and killmail_hash conflicts
                    try:
                        cur.execute("""
                            INSERT INTO killmails
                            (killmail_id, killmail_hash, killmail_time, solar_system_id,
                             victim_character_id, victim_corporation_id, victim_alliance_id,
                             victim_ship_id, is_npc)
                            VALUES (%(killmail_id)s, %(killmail_hash)s, %(killmail_time)s,
                                    %(solar_system_id)s, %(victim_character_id)s,
                                    %(victim_corporation_id)s, %(victim_alliance_id)s,
                                    %(victim_ship_id)s, %(is_npc)s)
                            ON CONFLICT (killmail_id) DO NOTHING
                        """, params)
                    except psycopg.errors.UniqueViolation:
                        # Hash conflict - already exists, skip this fit
                        conn.rollback()
                        self.stats['duplicates_skipped'] += 1
                        continue

                    # Insert fit (unique constraint prevents duplicates)
                    cur.execute("""
                        INSERT INTO fits
                        (killmail_id, ship_id, high_slots, med_slots, low_slots,
                         rig_slots, subsystem_slots, solar_system_id, killed_at)
                        VALUES (%(killmail_id)s, %(ship_id)s, %(high_slots)s,
                                %(med_slots)s, %(low_slots)s, %(rig_slots)s,
                                %(subsystem_slots)s, %(solar_system_id)s, %(killed_at)s)
                        ON CONFLICT (killmail_id) DO NOTHING
                    """, params)

                    if cur.rowcount > 0:
                        inserted += 1
                    else:
                        self.stats['duplicates_skipped'] += 1

                except Exception as e:
                    logger.error(f"Error inserting fit {fit.killmail_id}: {e}")

            conn.commit()

        return inserted

    def import_file(self, archive_path: Path) -> int:
        """
        Import fits from a single tar.bz2 file.

        Args:
            archive_path: Path to the tar.bz2 file

        Returns:
            Number of fits imported
        """
        logger.info(f"Processing {archive_path}...")

        batch = []
        imported = 0

        with self._get_conn() as conn:
            for killmail in self._parse_tar_bz2(archive_path):
                try:
                    fit = VictimFit.from_killmail(killmail)
                    self.stats['fits_extracted'] += 1
                    batch.append(fit)

                    if len(batch) >= self.batch_size:
                        inserted = self._insert_batch(conn, batch)
                        imported += inserted
                        self.stats['fits_imported'] += inserted
                        batch = []

                except Exception as e:
                    logger.warning(f"Error extracting fit: {e}")

            # Insert remaining batch
            if batch:
                inserted = self._insert_batch(conn, batch)
                imported += inserted
                self.stats['fits_imported'] += inserted

        self.stats['files_processed'] += 1
        logger.info(f"Imported {imported} fits from {archive_path}")
        return imported

    def import_date(self, date_str: str) -> int:
        """
        Download and import killmails for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Number of fits imported
        """
        archive_path = self._download_file(date_str, self.data_dir)
        return self.import_file(archive_path)

    def import_range(self, start_date: str, end_date: str) -> int:
        """
        Import killmails for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (inclusive)

        Returns:
            Number of fits imported
        """
        from datetime import datetime, timedelta

        current = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        total = 0
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            try:
                total += self.import_date(date_str)
            except Exception as e:
                logger.error(f"Failed to import {date_str}: {e}")

            current += timedelta(days=1)

        return total

    def print_stats(self):
        """Print import statistics."""
        logger.info("=" * 50)
        logger.info("Import Statistics:")
        logger.info(f"  Files processed: {self.stats['files_processed']}")
        logger.info(f"  Killmails seen: {self.stats['killmails_seen']}")
        logger.info(f"  Fits extracted: {self.stats['fits_extracted']}")
        logger.info(f"  Fits imported: {self.stats['fits_imported']}")
        logger.info(f"  Duplicates skipped: {self.stats['duplicates_skipped']}")
        logger.info("=" * 50)


def demo():
    """Demo the importer with a sample file."""
    importer = KillmailImporter()

    # Import a single day
    importer.import_date('2025-01-01')

    # Print stats
    importer.print_stats()

    # Check what we got
    with importer._get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT COUNT(*) as count FROM fits")
            print(f"\nTotal fits in database: {cur.fetchone()['count']}")

            cur.execute("""
                SELECT ship_id, COUNT(*) as count
                FROM fits
                GROUP BY ship_id
                ORDER BY count DESC
                LIMIT 10
            """)
            print("\nTop 10 ships:")
            for row in cur.fetchall():
                print(f"  Ship {row['ship_id']}: {row['count']} fits")


if __name__ == "__main__":
    demo()
