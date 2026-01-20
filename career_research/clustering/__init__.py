"""
Fit Clustering Module

Clusters ship fits by similarity using skill-based embeddings.

Process:
1. Generate skill requirements for each fit (via fit_resolver)
2. Create binary embeddings from skill sets
3. Store in pgvector
4. Cluster using cosine similarity + algorithm choice
5. Analyze clusters to find the "meta"
"""

from .embeddings import FitEmbedder

__all__ = ['FitEmbedder']
