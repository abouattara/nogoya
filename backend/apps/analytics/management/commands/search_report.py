"""Ce que les gens cherchent sur BINOGOYA, et ce qu'ils ne trouvent pas.

    python manage.py search_report                     # les 30 derniers jours
    python manage.py search_report --days 7
    python manage.py search_report --csv recherches.csv   # tout, pour un tableur

Le rapport sépare deux listes, parce qu'elles appellent deux gestes :

* les recherches **les plus fréquentes**, qui disent ce qui intéresse ;
* les recherches **sans résultat**, qui disent ce que le site n'a pas
  encore et qu'il faudrait aller chercher chez des fournisseurs.

Le fichier CSV ne contient ni numéro de téléphone ni nom : un identifiant
de membre ou un identifiant de visiteur anonyme, assez pour compter des
personnes distinctes, pas pour les reconnaître.
"""
import csv
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.analytics.models import SearchEvent


class Command(BaseCommand):
    help = "Résume les recherches : les plus fréquentes, et celles sans résultat."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Période, en jours (30 par défaut).")
        parser.add_argument("--top", type=int, default=20, help="Longueur des listes (20 par défaut).")
        parser.add_argument("--csv", metavar="FICHIER", help="Exporter toutes les recherches de la période.")

    def handle(self, *args, days, top, **options):
        csv_path = options.get("csv")
        since = timezone.now() - timedelta(days=days)
        events = SearchEvent.objects.filter(created_at__gte=since)

        total = events.count()
        people = (
            events.exclude(user__isnull=True).values("user").distinct().count()
            + events.filter(user__isnull=True).exclude(visitor_id="").values("visitor_id").distinct().count()
        )
        self.stdout.write(self.style.MIGRATE_HEADING(f"Recherches des {days} derniers jours"))
        self.stdout.write(f"  {total} recherches, par environ {people} personnes distinctes")

        by_channel = events.values("channel").annotate(n=Count("id")).order_by("-n")
        if by_channel:
            parts = ", ".join(f"{row['channel'] or 'inconnu'} : {row['n']}" for row in by_channel)
            self.stdout.write(f"  Par canal : {parts}")

        written = events.exclude(normalized_query="")

        self.stdout.write(self.style.MIGRATE_HEADING(f"\nLes {top} plus fréquentes"))
        for row in (
            written.values("normalized_query")
            .annotate(n=Count("id"), moyenne=Avg("results_count"))
            .order_by("-n", "normalized_query")[:top]
        ):
            self.stdout.write(
                f"  {row['n']:5d}  {row['normalized_query'][:50]:50s}  "
                f"~{row['moyenne']:.0f} résultat(s)"
            )

        self.stdout.write(self.style.MIGRATE_HEADING(f"\nLes {top} sans résultat : la demande non servie"))
        empty = (
            written.values("normalized_query")
            .annotate(n=Count("id"), servies=Count("id", filter=Q(results_count__gt=0)))
            .filter(servies=0)
            .order_by("-n", "normalized_query")[:top]
        )
        if not empty:
            self.stdout.write("  aucune")
        for row in empty:
            self.stdout.write(f"  {row['n']:5d}  {row['normalized_query'][:60]}")

        if csv_path:
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as handle:
                # utf-8-sig : Excel reconnaît alors les accents sans réglage.
                writer = csv_writer(handle)
                writer.writerow(["date", "recherche", "criteres", "resultats", "canal", "membre", "visiteur"])
                for event in events.order_by("created_at").iterator():
                    writer.writerow([
                        timezone.localtime(event.created_at).strftime("%Y-%m-%d %H:%M"),
                        event.query,
                        "; ".join(f"{k}={v}" for k, v in (event.filters or {}).items()),
                        event.results_count,
                        event.channel,
                        event.user_id or "",
                        event.visitor_id,
                    ])
            self.stdout.write(self.style.SUCCESS(f"\n{total} recherches exportées dans {csv_path}"))


def csv_writer(handle):
    # Le point-virgule : c'est le séparateur qu'attend un tableur réglé en
    # français, où la virgule sert aux décimales.
    return csv.writer(handle, delimiter=";")
