import time
from django.db import DatabaseError, connection
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class DatabaseHealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]
    LATENCY_THRESHOLD_MS = 200

    def get(self, request, *args, **kwargs):
        start = time.perf_counter()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

            degraded = elapsed_ms > self.LATENCY_THRESHOLD_MS
            return Response(
                {
                    "status": "degraded" if degraded else "ok",
                    "db_ms": elapsed_ms,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
                if degraded
                else status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "status": "error",
                    "db_ms": None,
                    "detail": "database unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
