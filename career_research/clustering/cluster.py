"""
Fit Clustering Pipeline

Clusters fits by similarity using pgvector cosine similarity.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ClusterResult:
    """Result of clustering a ship."""
    ship_id: int
    cluster_id: int
    fit_count: int
    # Representative fit (most central)
    representative_id: int
    # Sample fit IDs from this cluster
    sample_fits: List[int]


class FitClusterer:
    """
    Cluster fits by similarity using pgvector operators.

    pgvector operators:
    - <=> : cosine distance (1 - cosine_similarity)
    - <-> : L2 distance
    - <#> : negative inner product
    - <+> : L1 distance
    """

    def __init__(
        self,
        db_url: str = "postgresql://genie@/career_research",
        n_clusters: int = 5,
    ):
        """
        Initialize the clusterer.

        Args:
            db_url: PostgreSQL connection URL
            n_clusters: Number of clusters per ship (default: 5)
        """
        self.db_url = db_url
        self.n_clusters = n_clusters

    def cluster_ship(self, ship_id: int) -> List[ClusterResult]:
        """
        Cluster all fits for a specific ship using pgvector.

        Args:
            ship_id: Ship type ID to cluster

        Returns:
            List of ClusterResult objects
        """
        logger.info(f"Clustering ship {ship_id}...")

        with psycopg.connect(self.db_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # First, get count and check if we have embeddings
                cur.execute("""
                    SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE fit_vector IS NOT NULL) as with_vectors
                    FROM fits WHERE ship_id = %s
                """, [ship_id])

                stats = cur.fetchone()
                logger.info(f"Ship {ship_id}: {stats['with_vectors']}/{stats['total']} fits have embeddings")

                if stats['with_vectors'] == 0:
                    logger.warning(f"No embeddings for ship {ship_id}")
                    return []

                # Pick random cluster centers
                cur.execute("""
                    SELECT id as center_id
                    FROM fits
                    WHERE ship_id = %s AND fit_vector IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT %s
                """, [ship_id, self.n_clusters])

                centers = [row['center_id'] for row in cur]
                n_clusters = len(centers)

                # Clear existing clusters for this ship
                cur.execute("UPDATE fits SET cluster_id = NULL WHERE ship_id = %s", [ship_id])

                # Assign each fit to its nearest center using proper k-means logic
                # For each fit, find the closest center and assign it
                results = []

                # Build a CTE with all centers for distance comparison
                center_values = ', '.join([f"({cid}, {idx + 1})" for idx, cid in enumerate(centers)])

                cur.execute(f"""
                    WITH centers(center_id, cluster_num) AS (VALUES {center_values}),
                    distances AS (
                        SELECT
                            f.id,
                            c.cluster_num,
                            f.fit_vector <=> (SELECT fit_vector FROM fits WHERE id = c.center_id) as distance
                        FROM fits f
                        CROSS JOIN centers c
                        WHERE f.ship_id = %s AND f.fit_vector IS NOT NULL
                    ),
                    closest AS (
                        SELECT
                            id,
                            cluster_num
                        FROM distances
                        WHERE (id, distance) IN (
                            SELECT id, MIN(distance)
                            FROM distances
                            GROUP BY id
                        )
                    )
                    UPDATE fits f
                    SET cluster_id = c.cluster_num
                    FROM closest c
                    WHERE f.id = c.id
                """, [ship_id])

                conn.commit()

                # Query results directly (RETURNING doesn't work with this complex UPDATE)
                cur.execute("""
                    SELECT
                        cluster_id,
                        COUNT(*) as fit_count,
                        array_agg(id ORDER BY RANDOM()) as sample_ids
                    FROM fits
                    WHERE ship_id = %s AND cluster_id IS NOT NULL
                    GROUP BY cluster_id
                    ORDER BY cluster_id
                """, [ship_id])

                # Build a map of cluster_id -> results
                cluster_map = {row['cluster_id']: row for row in cur.fetchall()}

                # Build results in center order
                for cluster_idx, center_id in enumerate(centers):
                    cluster_id = cluster_idx + 1
                    if cluster_id in cluster_map:
                        row = cluster_map[cluster_id]
                        fit_count = row['fit_count']
                        sample_ids = row['sample_ids'][:10] if row['sample_ids'] else []

                        results.append(ClusterResult(
                            ship_id=ship_id,
                            cluster_id=cluster_id,
                            fit_count=fit_count,
                            representative_id=center_id,
                            sample_fits=sample_ids,
                        ))

        logger.info(f"Clustered ship {ship_id} into {len(results)} clusters")
        return results

    def get_similar_fits(self, fit_id: int, limit: int = 10, same_ship: bool = True) -> List[dict]:
        """
        Find fits similar to a given fit using pgvector <=> operator.

        Args:
            fit_id: Fit ID to find similarities for
            limit: Maximum number of results
            same_ship: Only return fits for the same ship

        Returns:
            List of similar fits with similarity scores
        """
        with psycopg.connect(self.db_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                ship_filter = "AND f.ship_id = ref.ship_id" if same_ship else ""

                cur.execute(f"""
                    SELECT
                        f.id,
                        f.ship_id,
                        1 - (f.fit_vector <=> ref.fit_vector) as similarity
                    FROM fits f, fits ref
                    WHERE ref.id = %s
                        AND f.id != %s
                        AND f.fit_vector IS NOT NULL
                        {ship_filter}
                    ORDER BY f.fit_vector <=> ref.fit_vector
                    LIMIT %s
                """, [fit_id, fit_id, limit])

                return cur.fetchall()

    def find_meta_fits(self, ship_id: int, top_n: int = 5) -> List[dict]:
        """
        Find the most common/representative fits for a ship.

        Uses vector similarity to cluster and find representatives.

        Args:
            ship_id: Ship type ID
            top_n: Number of top fits to return

        Returns:
            List of representative fits
        """
        # First cluster the ship
        self.cluster_ship(ship_id)

        # Get the largest clusters
        with psycopg.connect(self.db_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT
                        cluster_id,
                        COUNT(*) as fit_count,
                        array_agg(id ORDER BY id) as fit_ids,
                        (array_agg(id ORDER BY id))[1] as representative_id
                    FROM fits
                    WHERE ship_id = %s AND cluster_id IS NOT NULL
                    GROUP BY cluster_id
                    ORDER BY fit_count DESC
                    LIMIT %s
                """, [ship_id, top_n])

                return cur.fetchall()


def demo():
    """Demo clustering."""
    clusterer = FitClusterer(n_clusters=3)

    # Find similar fits first (doesn't require clustering)
    similar = clusterer.get_similar_fits(39714, limit=5)
    print(f"\nFits similar to fit 39714:")
    for s in similar:
        print(f"  Fit {s['id']} (ship {s['ship_id']}): {s['similarity']:.3f}")

    # Cluster a specific ship
    ship_id = 670  # Capsule
    results = clusterer.cluster_ship(ship_id)

    print(f"\nClustering results for ship {ship_id}:")
    for r in results:
        print(f"  Cluster {r.cluster_id}: {r.fit_count} fits")


if __name__ == "__main__":
    demo()
