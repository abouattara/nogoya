"""Import récurrent.

Une seule tâche, qui parcourt les sources actives et saute celles relancées
trop tôt. L'intervalle est porté par la source, pas par la planification :
un partenaire qui accepte un passage par jour le déclare une fois, et aucune
modification de `crontab` ne peut l'enfreindre par distraction.

Sur l'hébergement mutualisé, Celery tourne en mode « eager » (pas de
worker) : la planification se fait alors par une tâche cron appelant
`manage.py import_listings --all`. Voir DEPLOYMENT-CPANEL.md.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("nogoya.sourcing")


@shared_task
def run_scheduled_imports():
    """Exécute les sources actives dont l'intervalle est écoulé."""
    from .models import ListingSource
    from .services import run_import

    summaries = []
    for source in ListingSource.objects.filter(is_active=True):
        if source.last_run_at:
            due = source.last_run_at + timedelta(minutes=source.min_interval_minutes)
            if timezone.now() < due:
                logger.info("Source %s : prochaine exécution à %s", source.slug, due.isoformat())
                continue
        report = run_import(source)
        logger.info("Source %s : %s", source.slug, report.summary())
        summaries.append(report.as_dict())
    return summaries
