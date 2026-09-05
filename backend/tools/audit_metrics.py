"""Mesure locale : aucune valeur SQL, aucun jeton, aucune donnée client."""
from time import perf_counter
from django.db import connection


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        times = []

        def measure(execute, sql, params, many, context):
            start = perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                times.append((perf_counter() - start) * 1000)

        start = perf_counter()
        with connection.execute_wrapper(measure):
            response = self.get_response(request)
        response['X-Audit-Sql-Count'] = str(len(times))
        response['X-Audit-Sql-Ms'] = str(round(sum(times), 3))
        response['X-Audit-Slowest-Sql-Ms'] = str(round(max(times, default=0), 3))
        response['X-Audit-App-Ms'] = str(round((perf_counter() - start) * 1000, 3))
        return response
