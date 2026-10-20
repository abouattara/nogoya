"""Effacer les données brutes conservées pour diagnostic.

`ListingImport.raw_payload` garde la réponse de la source pour comprendre un
import raté. Passé quelques semaines, elle n'apprend plus rien et devient
une collecte de données qu'on ne saurait plus justifier. On la vide, la
ligne et son statut restant intacts.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.sourcing.models import ListingImport

DEFAULT_DAYS = 30


class Command(BaseCommand):
    help = "Vide les données brutes des imports plus anciens que --days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        stale = ListingImport.objects.filter(collected_at__lt=cutoff).exclude(raw_payload={})
        count = stale.count()

        if options["dry_run"]:
            self.stdout.write(f"{count} import(s) verraient leurs données brutes effacées.")
            return

        stale.update(raw_payload={})
        self.stdout.write(self.style.SUCCESS(f"{count} import(s) purgé(s) (antérieurs à {cutoff:%Y-%m-%d})."))
