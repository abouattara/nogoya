"""Lancer un import à la main.

    python manage.py import_listings --source agence-exemple --limit 20 --dry-run
    python manage.py import_listings --all

`--dry-run` lit la source et dit ce qui se passerait, sans rien écrire :
c'est ce qu'on lance en premier après avoir configuré une source, avant de
laisser l'automatisation s'en occuper.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.sourcing.models import ListingSource
from apps.sourcing.services import run_import


class Command(BaseCommand):
    help = "Importe les annonces des sources autorisées et actives."

    def add_arguments(self, parser):
        parser.add_argument("--source", help="Identifiant (slug) d'une source précise.")
        parser.add_argument("--all", action="store_true", help="Toutes les sources actives.")
        parser.add_argument("--limit", type=int, help="Plafond d'annonces pour cette exécution.")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="N'écrit rien : affiche seulement ce qui serait fait.",
        )

    def handle(self, *args, **options):
        if options["source"]:
            sources = ListingSource.objects.filter(slug=options["source"])
            if not sources.exists():
                raise CommandError(f"Aucune source « {options['source']} ».")
        elif options["all"]:
            sources = ListingSource.objects.filter(is_active=True)
            if not sources.exists():
                self.stdout.write(self.style.WARNING("Aucune source active."))
                return
        else:
            raise CommandError("Précisez --source <slug> ou --all.")

        failures = 0
        for source in sources:
            report = run_import(source, limit=options["limit"], dry_run=options["dry_run"])
            style = self.style.SUCCESS
            if report.status == ListingSource.RunStatus.FAILED:
                style, failures = self.style.ERROR, failures + 1
            elif report.status == ListingSource.RunStatus.PARTIAL:
                style = self.style.WARNING
            self.stdout.write(style(report.summary()))
            for error in report.errors[:10]:
                self.stdout.write(f"    · {error}")

        if options["dry_run"]:
            self.stdout.write(self.style.NOTICE("Simulation : rien n'a été écrit."))
        if failures:
            raise CommandError(f"{failures} source(s) en échec.")
