"""
Fit Embedding Generation

Converts fits into vectors for clustering using skill requirements.
"""

import logging
import sqlite3
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
import numpy as np

# For direct execution, add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from fit_resolver.resolver import FitResolver, SkillRequirement

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FitEmbedder:
    """
    Generate embeddings for fits based on skill requirements.

    Two embedding strategies:
    1. Binary skill presence: 3500-dim vector, 1 if skill required
    2. Skill-level pairs: Higher dimension, captures skill level

    Vectors are normalized for cosine similarity search.
    """

    def __init__(
        self,
        db_url: str = "postgresql://genie@/career_research",
        sde_path: Optional[str] = None,
        embedding_dim: Optional[int] = None,
    ):
        """
        Initialize the embedder.

        Args:
            db_url: PostgreSQL connection URL
            sde_path: Path to SQLite SDE database
            embedding_dim: Force specific dimension (None = auto-detect from skills)
        """
        self.db_url = db_url
        self.sde_path = sde_path or str(Path('~/data/evewire/eve_sde.sqlite3').expanduser())
        self.embedding_dim = embedding_dim

        self.resolver = FitResolver(self.sde_path)

        # Load skill ID mappings
        self._load_skills()

    def _load_skills(self):
        """Load all skill IDs and create index mapping."""
        conn = sqlite3.connect(self.sde_path)
        conn.row_factory = sqlite3.Row

        # Get all skills (groupID 16 is "Skills" but there are other skill groups)
        # Actually, let's get all items that have skill requirements
        rows = conn.execute("""
            SELECT DISTINCT typeID, typeName
            FROM invTypes
            WHERE groupID IN (
                SELECT groupID FROM invGroups
                WHERE categoryID = 16  -- Skills category
            )
            ORDER BY typeID
        """).fetchall()

        self.skill_ids = [r['typeID'] for r in rows]
        self.skill_id_to_idx = {sid: i for i, sid in enumerate(self.skill_ids)}
        self.num_skills = len(self.skill_ids)

        if self.embedding_dim is None:
            self.embedding_dim = self.num_skills

        logger.info(f"Loaded {self.num_skills} skills, embedding_dim={self.embedding_dim}")

        conn.close()

    def fit_to_skills(self, fit_data: dict) -> Set[int]:
        """
        Convert a fit from database to skill requirements.

        Args:
            fit_data: Dict with ship_id, high_slots, med_slots, etc.

        Returns:
            Set of skill IDs required
        """
        # Convert to fit_resolver format
        resolver_data = {
            "ship": fit_data['ship_id'],
            "highs": fit_data.get('high_slots', []),
            "meds": fit_data.get('med_slots', []),
            "lows": fit_data.get('low_slots', []),
            "rigs": fit_data.get('rig_slots', []),
            "subsystems": fit_data.get('subsystem_slots', []),
        }

        requirements = self.resolver.resolve_fit_dict(resolver_data)
        return {req.skill_id for req in requirements}

    def embed_skills(self, skill_ids: Set[int]) -> List[float]:
        """
        Convert a set of skill IDs to a binary embedding vector.

        Args:
            skill_ids: Set of required skill IDs

        Returns:
            Normalized binary vector as list of floats
        """
        # Create binary vector
        vector = np.zeros(self.embedding_dim, dtype=np.float32)

        for skill_id in skill_ids:
            if skill_id in self.skill_id_to_idx:
                idx = self.skill_id_to_idx[skill_id]
                if idx < self.embedding_dim:
                    vector[idx] = 1.0

        # Normalize for cosine similarity
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.tolist()

    def generate_embeddings_batch(self, limit: Optional[int] = None, batch_size: int = 500) -> int:
        """
        Generate embeddings for all fits that don't have one yet.

        Args:
            limit: Maximum number of fits to process (None = all)
            batch_size: Batch size for database updates

        Returns:
            Number of embeddings generated
        """
        logger.info("Generating fit embeddings...")

        count = 0
        batch_updates = []

        with psycopg.connect(self.db_url) as conn:
            # Get fits without embeddings
            with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    SELECT id, ship_id, high_slots, med_slots, low_slots,
                           rig_slots, subsystem_slots
                    FROM fits
                    WHERE fit_vector IS NULL
                    ORDER BY id
                """
                if limit:
                    query += f" LIMIT {limit}"

                cur.execute(query)

                for row in cur:
                    try:
                        # Convert db arrays to lists
                        fit_data = {
                            'ship_id': row['ship_id'],
                            'high_slots': list(row['high_slots'] or []),
                            'med_slots': list(row['med_slots'] or []),
                            'low_slots': list(row['low_slots'] or []),
                            'rig_slots': list(row['rig_slots'] or []),
                            'subsystem_slots': list(row['subsystem_slots'] or []),
                        }

                        # Get skills and embed
                        skill_ids = self.fit_to_skills(fit_data)
                        embedding = self.embed_skills(skill_ids)

                        batch_updates.append((row['id'], embedding))

                        if len(batch_updates) >= batch_size:
                            self._update_embeddings(conn, batch_updates)
                            count += len(batch_updates)
                            batch_updates = []

                            if count % 10000 == 0:
                                logger.info(f"Generated {count} embeddings...")

                    except Exception as e:
                        logger.warning(f"Error embedding fit {row['id']}: {e}")

                # Final batch
                if batch_updates:
                    self._update_embeddings(conn, batch_updates)
                    count += len(batch_updates)

        logger.info(f"Generated {count} embeddings total")
        return count

    def _update_embeddings(self, conn, updates: List[Tuple[int, List[float]]]):
        """Batch update embeddings in database."""
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE fits SET fit_vector = %s::vector WHERE id = %s",
                [(emb, fit_id) for fit_id, emb in updates]
            )
            conn.commit()


def demo():
    """Demo the embedder."""
    embedder = FitEmbedder()

    # Generate embeddings
    count = embedder.generate_embeddings_batch(limit=100)
    print(f"Generated {count} embeddings")

    # Check stats
    with psycopg.connect(embedder.db_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE fit_vector IS NOT NULL) as with_vector
                FROM fits
            """)
            row = cur.fetchone()
            print(f"Total fits: {row['total']}, with embeddings: {row['with_vector']}")

            cur.execute("""
                SELECT id, ship_id
                FROM fits
                WHERE fit_vector IS NOT NULL
                LIMIT 5
            """)
            print("Sample fits with embeddings:")
            for row in cur:
                print(f"  Fit {row['id']}, ship {row['ship_id']}")


if __name__ == "__main__":
    demo()
