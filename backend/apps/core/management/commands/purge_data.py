"""Vider le site de ses données de démonstration, ou de toutes ses annonces.

Une suppression en production ne se rattrape pas. Trois garde-fous, et ils
ne sont pas négociables :

* **La simulation est le défaut.** Sans `--yes`, rien n'est écrit ; la
  commande se contente de compter ce qu'elle supprimerait.
* **Aucun compte d'équipe n'est touché.** Un superutilisateur ou un membre
  du personnel est exclu de toute suppression, même s'il figure dans la
  liste des comptes de démonstration — se verrouiller dehors de son propre
  site est une erreur qu'on ne commet qu'une fois.
* **Le détail avant l'action.** Le décompte est affiché par modèle, et
  l'ordre de suppression suit les dépendances.

    python manage.py purge_data                      # simulation « démo »
    python manage.py purge_data --yes                # supprime les données de démo
    python manage.py purge_data --scope all          # simulation « tout »
    python manage.py purge_data --scope all --yes    # supprime toutes les annonces

Les fichiers images ne partent pas avec les lignes : Django laisse les
octets derrière lui. Enchaînez toujours avec :

    python manage.py prune_media --delete
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.analytics.models import ContactEvent, ProductView
from apps.catalog.models import Favorite, Product
from apps.core.management.commands.seed_demo import DEMO_PHONES
from apps.messaging.models import Conversation, Message
from apps.notifications.models import Notification

User = get_user_model()


class Command(BaseCommand):
    help = "Supprime les données de démonstration, ou toutes les annonces."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scope", choices=["demo", "all"], default="demo",
            help=(
                "demo : les comptes semés par seed_demo et tout ce qu'ils possèdent. "
                "all : toutes les annonces et tout ce qui s'y rattache, les comptes "
                "et les catégories étant conservés."
            ),
        )
        parser.add_argument(
            "--phone", action="append", default=[],
            help="Compte supplémentaire à supprimer (répétable). Ignoré si équipe.",
        )
        parser.add_argument(
            "--yes", action="store_true",
            help="Applique réellement. Sans ce drapeau, rien n'est écrit.",
        )

    def handle(self, *args, **options):
        scope = options["scope"]
        apply_changes = options["yes"]

        if scope == "demo":
            plan = self._demo_plan(options["phone"])
        else:
            plan = self._everything_plan()

        total = sum(count for _, count in plan["counts"])
        self.stdout.write(self.style.MIGRATE_HEADING(f"Portée : {scope}"))
        for label, count in plan["counts"]:
            self.stdout.write(f"  {label:34s} {count:6d}")
        self.stdout.write(f"  {'TOTAL':34s} {total:6d}")

        if plan["protected"]:
            self.stdout.write(
                self.style.WARNING(
                    "\nComptes d'équipe conservés : " + ", ".join(plan["protected"])
                )
            )

        if total == 0:
            self.stdout.write(self.style.SUCCESS("\nRien à supprimer."))
            return

        if not apply_changes:
            self.stdout.write(
                self.style.NOTICE("\nSimulation : rien n'a été écrit. Ajoutez --yes pour agir.")
            )
            return

        with transaction.atomic():
            plan["execute"]()

        self.stdout.write(self.style.SUCCESS(f"\n{total} enregistrement(s) supprimé(s)."))
        self.stdout.write(
            "Les fichiers images sont encore sur le disque. Enchaînez avec :\n"
            "    python manage.py prune_media            # pour voir\n"
            "    python manage.py prune_media --delete   # pour supprimer"
        )

    # ------------------------------------------------------------------
    def _demo_plan(self, extra_phones):
        wanted = [*DEMO_PHONES, *extra_phones]
        accounts = User.objects.filter(phone__in=wanted)

        # Un compte d'équipe n'est jamais supprimé, quel que soit son numéro.
        protected = list(
            accounts.filter(is_staff=True).values_list("phone", flat=True)
        ) + list(accounts.filter(is_superuser=True).values_list("phone", flat=True))
        deletable = accounts.exclude(is_staff=True).exclude(is_superuser=True)

        products = Product.objects.filter(supplier__user__in=deletable)
        conversations = Conversation.objects.filter(
            participant_low__in=deletable
        ) | Conversation.objects.filter(participant_high__in=deletable)

        counts = [
            ("Comptes de démonstration", deletable.count()),
            ("Annonces de ces comptes", products.count()),
            ("Conversations", conversations.distinct().count()),
            ("Favoris", Favorite.objects.filter(user__in=deletable).count()),
            ("Notifications", Notification.objects.filter(user__in=deletable).count()),
        ]

        def execute():
            # Les annonces d'abord : la cascade depuis le compte y arriverait
            # aussi, mais l'ordre explicite rend le décompte vérifiable.
            products.delete()
            conversations.distinct().delete()
            deletable.delete()

        return {"counts": counts, "protected": sorted(set(protected)), "execute": execute}

    def _everything_plan(self):
        products = Product.objects.all()
        counts = [
            ("Annonces", products.count()),
            ("Conversations", Conversation.objects.count()),
            ("Messages", Message.objects.count()),
            ("Favoris", Favorite.objects.count()),
            ("Vues d'annonce", ProductView.objects.count()),
            ("Contacts enregistrés", ContactEvent.objects.count()),
            ("Notifications", Notification.objects.count()),
        ]

        def execute():
            # Les catégories, leurs attributs et les comptes survivent : ce
            # sont la structure du site, pas son contenu de test.
            products.delete()
            Conversation.objects.all().delete()
            Message.objects.all().delete()
            Favorite.objects.all().delete()
            ProductView.objects.all().delete()
            ContactEvent.objects.all().delete()
            Notification.objects.all().delete()

        return {"counts": counts, "protected": [], "execute": execute}
