"""
Zkillboard Killmail Ingestion

Downloads and processes EVE Online killmail data from EvereF data dumps.
Extracts victim fits (ship + fitted modules) and stores in PostgreSQL.

Data source: https://data.everef.net/killmails/
"""

from .ingest import KillmailImporter, SlotFlag

__all__ = ['KillmailImporter', 'SlotFlag']
