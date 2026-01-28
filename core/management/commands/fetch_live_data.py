"""
Django management command to fetch live ESI data.

Run: python manage.py fetch_live_data [options]

Examples:
    python manage.py fetch_live_data --all
    python manage.py fetch_live_data --incursions
    python manage.py fetch_live_data --lp-stores --wars
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

logger = logging.getLogger('evewire')


class Command(BaseCommand):
    help = 'Fetch and cache live ESI data for the Live Universe Browser'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Fetch all live data types',
        )
        parser.add_argument(
            '--lp-stores',
            action='store_true',
            help='Fetch loyalty point stores',
        )
        parser.add_argument(
            '--incursions',
            action='store_true',
            help='Fetch active incursions',
        )
        parser.add_argument(
            '--wars',
            action='store_true',
            help='Fetch active wars',
        )
        parser.add_argument(
            '--sovereignty',
            action='store_true',
            help='Fetch sovereignty data',
        )
        parser.add_argument(
            '--fw',
            '--faction-warfare',
            action='store_true',
            dest='fw',
            help='Fetch faction warfare data',
        )
        parser.add_argument(
            '--markets',
            action='store_true',
            help='Fetch market summaries (requires region IDs)',
        )
        parser.add_argument(
            '--region',
            type=int,
            action='append',
            help='Region ID for market data (can be specified multiple times)',
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress informational output',
        )

    def handle(self, *args, **options):
        """Execute the fetch command."""
        from core.eve.tasks import (
            refresh_all_lp_stores,
            refresh_incursions,
            refresh_wars,
            refresh_sov_map,
            refresh_sov_campaigns,
            refresh_fw_stats,
            refresh_fw_systems,
            refresh_region_market_summary,
        )

        quiet = options.get('quiet', False)
        fetch_all = options.get('all', False)

        # Track what we're fetching
        fetch_counts = {}
        start_time = timezone.now()

        def log(message, level='info'):
            """Log to both stdout and logger."""
            if not quiet:
                if level == 'success':
                    self.stdout.write(self.style.SUCCESS(message))
                elif level == 'warning':
                    self.stdout.write(self.style.WARNING(message))
                elif level == 'error':
                    self.stdout.write(self.style.ERROR(message))
                else:
                    self.stdout.write(message)
            logger.info(message)

        # Helper to execute and track
        def fetch_task(name, task_func, *args, **kwargs):
            """Execute a fetch task and track results."""
            try:
                log(f'Fetching {name}...')
                result = task_func(*args, **kwargs)
                status = result.get('status', 'unknown')
                count = result.get('count', result.get('offers', result.get('queued', 0)))
                fetch_counts[name] = {'status': status, 'count': count}

                if status == 'ok' or status == 'queued':
                    log(f'  {name}: {status} ({count} items)', 'success')
                else:
                    log(f'  {name}: {status}', 'warning')
                    if result.get('message'):
                        log(f'    {result["message"]}', 'warning')
            except Exception as e:
                fetch_counts[name] = {'status': 'error', 'count': 0, 'error': str(e)}
                log(f'  {name}: ERROR - {e}', 'error')

        # Loyalty Stores
        if fetch_all or options.get('lp_stores'):
            fetch_task('LP Stores', refresh_all_lp_stores)

        # Incursions
        if fetch_all or options.get('incursions'):
            fetch_task('Incursions', refresh_incursions)

        # Wars
        if fetch_all or options.get('wars'):
            fetch_task('Wars', refresh_wars)

        # Sovereignty
        if fetch_all or options.get('sovereignty'):
            fetch_task('Sov Map', refresh_sov_map)
            fetch_task('Sov Campaigns', refresh_sov_campaigns)

        # Faction Warfare
        if fetch_all or options.get('fw'):
            fetch_task('FW Stats', refresh_fw_stats)
            fetch_task('FW Systems', refresh_fw_systems)

        # Markets
        if fetch_all or options.get('markets'):
            regions = options.get('region', [])
            if regions:
                for region_id in regions:
                    fetch_task(f'Market Region {region_id}', refresh_region_market_summary, region_id)
            else:
                # Default to major trade hubs if no regions specified
                default_regions = [10000002, 10000043, 10000032]  # Jita, Amarr, Dodixie
                log('No regions specified, fetching major trade hubs...', 'warning')
                for region_id in default_regions:
                    fetch_task(f'Market Region {region_id}', refresh_region_market_summary, region_id)

        # Summary
        elapsed = (timezone.now() - start_time).total_seconds()

        if fetch_counts:
            log('')
            log('=' * 50)
            log('Fetch Summary', 'success')
            log('=' * 50)

            total_items = sum(v.get('count', 0) for v in fetch_counts.values())
            success_count = sum(1 for v in fetch_counts.values() if v.get('status') in ('ok', 'queued'))
            error_count = len(fetch_counts) - success_count

            for name, result in fetch_counts.items():
                status_emoji = '✓' if result['status'] in ('ok', 'queued') else '✗'
                log(f'{status_emoji} {name}: {result["status"]} ({result["count"]} items)')

            log('')
            log(f'Total: {len(fetch_counts)} data types, {total_items} items in {elapsed:.1f}s')

            if error_count > 0:
                log(f'{error_count} errors encountered', 'warning')
            else:
                log('All fetches completed successfully', 'success')
        else:
            log('No data types specified. Use --help for options.', 'warning')
            log('Common usage: python manage.py fetch_live_data --all', 'info')
