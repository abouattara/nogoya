from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse


def health(request):
    """Lightweight liveness endpoint for monitoring / smoke tests."""
    return JsonResponse({"status": "ok"})


def ready(request):
    """Readiness: can this instance actually serve traffic right now?"""
    checks = {}
    try:
        connections["default"].cursor()
        checks["database"] = "ok"
    except OperationalError:
        checks["database"] = "error"
    try:
        cache.set("readyz", "1", timeout=5)
        checks["cache"] = "ok" if cache.get("readyz") == "1" else "error"
    except Exception:
        checks["cache"] = "error"

    healthy = all(v == "ok" for v in checks.values())
    return JsonResponse({"status": "ok" if healthy else "error", "checks": checks}, status=200 if healthy else 503)
