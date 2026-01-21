"""
Cluster Analysis and Canonical Fit Extraction

Analyzes clusters of similar fits and extracts representative "canonical" fits.
"""

import logging
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class CanonicalFit:
    """A representative fit extracted from a cluster."""
    ship_id: int
    ship_name: str
    cluster_id: int
    fit_count: int
    # Most common modules per slot
    high_slots: List[Tuple[int, str, int]]  # (typeID, name, count)
    med_slots: List[Tuple[int, str, int]]
    low_slots: List[Tuple[int, str, int]]
    rig_slots: List[Tuple[int, str, int]]
    subsystem_slots: List[Tuple[int, str, int]]
    # Stats
    avg_similarity: float

    def format(self) -> str:
        """Format as EFT-style string."""
        lines = [f"[{self.ship_name}, cluster {self.cluster_id}]"]
        lines.append(f"// {self.fit_count} fits, avg similarity: {self.avg_similarity:.3f}")
        lines.append("")

        slot_names = {
            'high_slots': 'Highs',
            'med_slots': 'Meds',
            'low_slots': 'Lows',
            'rig_slots': 'Rigs',
            'subsystem_slots': 'Subsystems',
        }

        for slot_attr, slot_name in slot_names.items():
            modules = getattr(self, slot_attr)
            if modules:
                lines.append(f"{slot_name}:")
                for type_id, name, count in modules:
                    pct = 100 * count / self.fit_count
                    lines.append(f"  {name} ({type_id}) - {pct:.1f}%")

        return "\n".join(lines)


class ClusterAnalyzer:
    """
    Analyze clusters and extract canonical fits.

    Approach:
    1. Get all fits in a cluster
    2. For each slot position, find the most common module
    3. Compute statistics (usage percentage, etc.)
    4. Return a "canonical" fit representing the cluster
    """

    def __init__(
        self,
        db_url: str = "postgresql://genie@/career_research",
        sde_path: Optional[str] = None,
    ):
        """
        Initialize the analyzer.

        Args:
            db_url: PostgreSQL connection URL
            sde_path: Path to SQLite SDE database for item names
        """
        self.db_url = db_url
        self.sde_path = sde_path or "/home/genie/gt/evewire/crew/aura/db.sqlite3"
        self._ammo_cache = None  # Cache for ammo type IDs

    def get_ship_name(self, ship_id: int) -> str:
        """Get ship name from SDE."""
        import sqlite3
        conn = sqlite3.connect(self.sde_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT typeName FROM invTypes WHERE typeID = ?", [ship_id]
        ).fetchone()
        conn.close()
        return row["typeName"] if row else f"Ship {ship_id}"

    def get_module_name(self, type_id: int) -> str:
        """Get module name from SDE."""
        import sqlite3
        conn = sqlite3.connect(self.sde_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT typeName FROM invTypes WHERE typeID = ?", [type_id]
        ).fetchone()
        conn.close()
        return row["typeName"] if row else f"Module {type_id}"

    def _is_ammo(self, type_id: int) -> bool:
        """Check if type_id is ammo/charge (category 8). Uses cache."""
        if self._ammo_cache is None:
            # Initialize cache: load all ammo type IDs from category 8
            import sqlite3
            conn = sqlite3.connect(self.sde_path)
            self._ammo_cache = set(
                row[0] for row in conn.execute(
                    "SELECT t.typeID FROM invTypes t JOIN invGroups g ON t.groupID = g.groupID WHERE g.categoryID = 8"
                )
            )
            conn.close()
            logger.info(f"Loaded {len(self._ammo_cache)} ammo type IDs into cache")
        return type_id in self._ammo_cache

    def extract_canonical_fit(self, ship_id: int, cluster_id: int) -> Optional[CanonicalFit]:
        """
        Extract a canonical fit from a cluster.

        Args:
            ship_id: Ship type ID
            cluster_id: Cluster ID

        Returns:
            CanonicalFit object or None if cluster not found
        """
        logger.info(f"Extracting canonical fit for ship {ship_id}, cluster {cluster_id}")

        with psycopg.connect(self.db_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Get all fits in this cluster
                cur.execute("""
                    SELECT
                        id,
                        ship_id,
                        high_slots,
                        med_slots,
                        low_slots,
                        rig_slots,
                        subsystem_slots,
                        fit_vector
                    FROM fits
                    WHERE ship_id = %s AND cluster_id = %s
                """, [ship_id, cluster_id])

                fits = list(cur.fetchall())

                if not fits:
                    logger.warning(f"No fits found for ship {ship_id}, cluster {cluster_id}")
                    return None

                logger.info(f"Found {len(fits)} fits in cluster")

                # Compute average similarity to cluster center
                # (use first fit as reference for now)
                avg_similarity = 0.8  # Placeholder

                # Extract most common modules per slot
                slot_attrs = ['high_slots', 'med_slots', 'low_slots', 'rig_slots', 'subsystem_slots']
                slot_modules = {}

                for slot_attr in slot_attrs:
                    # Count module occurrences at each position
                    position_counts = defaultdict(Counter)

                    for fit in fits:
                        modules = fit[slot_attr] or []
                        for i, module_id in enumerate(modules):
                            if module_id and not self._is_ammo(module_id):
                                position_counts[i][module_id] += 1

                    # For each slot position, get the most common module
                    # (up to 8 positions for most slots)
                    slot_modules[slot_attr] = []
                    for pos in sorted(position_counts.keys()):
                        if pos >= 8:  # Max 8 slots per type
                            continue
                        counter = position_counts[pos]
                        if counter:
                            most_common = counter.most_common(1)[0]
                            module_id, count = most_common
                            module_name = self.get_module_name(module_id)
                            slot_modules[slot_attr].append((module_id, module_name, count))

                ship_name = self.get_ship_name(ship_id)

                return CanonicalFit(
                    ship_id=ship_id,
                    ship_name=ship_name,
                    cluster_id=cluster_id,
                    fit_count=len(fits),
                    high_slots=slot_modules.get('high_slots', []),
                    med_slots=slot_modules.get('med_slots', []),
                    low_slots=slot_modules.get('low_slots', []),
                    rig_slots=slot_modules.get('rig_slots', []),
                    subsystem_slots=slot_modules.get('subsystem_slots', []),
                    avg_similarity=avg_similarity,
                )

    def analyze_ship_clusters(self, ship_id: int, limit: int = 5) -> List[CanonicalFit]:
        """
        Analyze all clusters for a ship.

        Args:
            ship_id: Ship type ID
            limit: Maximum number of clusters to analyze

        Returns:
            List of CanonicalFit objects
        """
        with psycopg.connect(self.db_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Get clusters for this ship, sorted by size
                cur.execute("""
                    SELECT cluster_id, COUNT(*) as fit_count
                    FROM fits
                    WHERE ship_id = %s AND cluster_id IS NOT NULL
                    GROUP BY cluster_id
                    ORDER BY fit_count DESC
                    LIMIT %s
                """, [ship_id, limit])

                clusters = list(cur.fetchall())

        logger.info(f"Found {len(clusters)} clusters for ship {ship_id}")

        canonical_fits = []
        for cluster in clusters:
            canonical = self.extract_canonical_fit(ship_id, cluster['cluster_id'])
            if canonical:
                canonical_fits.append(canonical)

        return canonical_fits

    def find_popular_ships(self, limit: int = 10) -> List[Tuple[int, str, int]]:
        """
        Find ships with the most fits that have embeddings.

        Args:
            limit: Maximum number of ships to return

        Returns:
            List of (ship_id, ship_name, fit_count) tuples
        """
        with psycopg.connect(self.db_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT ship_id, COUNT(*) as fit_count
                    FROM fits
                    WHERE fit_vector IS NOT NULL
                    GROUP BY ship_id
                    ORDER BY fit_count DESC
                    LIMIT %s
                """, [limit])

                results = []
                for row in cur:
                    ship_name = self.get_ship_name(row['ship_id'])
                    results.append((row['ship_id'], ship_name, row['fit_count']))

                return results


def demo():
    """Demo cluster analysis."""
    analyzer = ClusterAnalyzer()

    # Find popular ships
    print("=" * 60)
    print("Popular Ships (with embeddings)")
    print("=" * 60)
    popular = analyzer.find_popular_ships(limit=10)
    for ship_id, ship_name, count in popular:
        print(f"  {ship_name}: {count} fits")

    # Analyze top ship's clusters
    if popular:
        top_ship_id, top_ship_name, _ = popular[0]

        print(f"\n{'=' * 60}")
        print(f"Analyzing {top_ship_name}")
        print("=" * 60)

        # First, let's cluster this ship
        from .cluster import FitClusterer
        clusterer = FitClusterer(n_clusters=3)
        clusterer.cluster_ship(top_ship_id)

        # Now extract canonical fits
        canonical_fits = analyzer.analyze_ship_clusters(top_ship_id, limit=3)

        for canonical in canonical_fits:
            print("\n" + canonical.format())
            print("-" * 60)


if __name__ == "__main__":
    demo()
