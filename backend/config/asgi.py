"""ASGI entrypoint.

Plain HTTP. The chat refreshes by polling, so there is no WebSocket layer:
Channels and its Redis channel layer were removed rather than kept running
a router with no routes. Re-adding them is a contained change — see
ARCHITECTURE.md ("Temps réel").
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_asgi_application()
