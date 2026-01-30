"""
Performance monitoring middleware for catching N+1 queries and slow requests.
"""
import time
import logging
from django.conf import settings

logger = logging.getLogger('evewire.performance')


class PerformanceMonitoringMiddleware:
    """
    Logs request performance metrics to help identify N+1 queries and slow views.

    Logs when:
    - Request takes longer than SLOW_REQUEST_THRESHOLD (default 500ms)
    - SQL query count exceeds EXCESSIVE_QUERIES_THRESHOLD (default 50)

    Only active when DEBUG=True.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 0.5)  # 500ms
        self.excessive_queries = getattr(settings, 'EXCESSIVE_QUERIES_THRESHOLD', 50)

    def __call__(self, request):
        if not settings.DEBUG:
            return self.get_response(request)

        start_time = time.time()

        response = self.get_response(request)

        duration = time.time() - start_time

        # Get SQL query count from django.db.connection
        from django.db import connection
        query_count = len(connection.queries)

        # Log slow requests
        if duration > self.slow_threshold:
            logger.warning(
                f'SLOW REQUEST: {request.method} {request.path} '
                f'took {duration*1000:.0f}ms with {query_count} queries'
            )

        # Log excessive query counts (potential N+1)
        if query_count > self.excessive_queries:
            logger.warning(
                f'EXCESSIVE QUERIES: {request.method} {request.path} '
                f'executed {query_count} SQL queries in {duration*1000:.0f}ms'
            )

        # Add performance headers to response (helpful for browser dev tools)
        response['X-Request-Duration'] = f'{duration*1000:.0f}ms'
        response['X-SQL-Queries'] = str(query_count)

        return response
