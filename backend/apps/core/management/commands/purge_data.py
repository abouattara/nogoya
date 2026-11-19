"""Vider le site de ses données de démonstration, ou de tout son contenu de test.

Une suppression en production ne se rattrape pas. Quatre garde-fous, et ils
ne sont pas négociables :

* **La simulation est le défaut.** Sans `--yes`, rien n'est écrit ; la
  commande se contente de compter ce qu'elle supprimerait.
* **Aucun compte d'équipe n'est touché.** Un superutilisateur, un membre du
  personnel ou le compte « Équipe BINOGOYA » qui signe les messages du
  support est exclu de toute suppression, même s'il figure dans une liste.
  Se verrouiller dehors de son propre site est une erreur qu'on ne commet
  qu'une fois.
* **Les comptes ne partent que si on le demande.** `--scope all` vide le
  contenu et garde les membres ; `--with-accounts` est un second choix,
  explicite, et la simulation affiche les numéros concernés avant.
* **Le détail avant l'action.** Le décompte est affiché par modèle, et
  l'ordre de suppression suit les dépendances.

    python manage.py purge_data                          # simulation « démo »
    python manage.py purge_data --yes                    # supprime la démo
    python manage.py purge_data --scope all              # simulation « tout »
    python manage.py purge_data --scope all --yes        # vide le contenu, garde les comptes
    python manage.py purge_data --scope all --with-accounts --keep-phone +226...   # et les comptes

Ce qui survit toujours : les catégories et leurs critères, les sources
d'import autorisées, les comptes d'équipe, et les acceptations des
conditions des comptes conservés.

Les fichiers (photos, vocaux, pièces jointes) ne partent pas avec les
lignes : Django laisse les octets derrière lui. Enchaînez toujours avec :

    python manage.py prune_media --delete
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.analytics.models import ContactEvent, ProductView, SearchEvent
from apps.catalog.models import Favorite, Product
from apps.core.management.commands.seed_demo import DEMO_PHONES
from apps.live.models import LiveSession
from apps.messaging.models import Conversation, Message
from apps.messaging.services import SUPPORT_PHONE
from apps.notifications.models import Notification
from apps.rentals.models import RentalRequest
from apps.sourcing.models import ListingImport

User = get_user_model()

#: Au-delà, la simulation résume la liste des numéros au lieu de l'afficher.
SHOWN_PHONES = 60


def team_accounts():
    """Les comptes qu'aucune purge ne supprime."""
    return User.objects.filter(Q(is_staff=True) | Q(is_superuser=True) | Q(phone=SUPPORT_PHONE))


class Command(BaseCommand):
    help = "Supprime les données de démonstration, ou tout le contenu de test."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scope", choices=["demo", "all"], default="demo",
            help=(
                "demo : les comptes semés par seed_demo et tout ce qu'ils possèdent. "
                "all : toutes les annonces, conversations, demandes, directs, "
                "statistiques et notifications ; les comptes sont conservés."
            ),
        )
        parser.add_argument(
            "--phone", action="append", default=[],
            help="Compte supplémentaire à supprimer (répétable). Ignoré si équipe.",
        )
        parser.add_argument(
            "--with-accounts", action="store_true",
            help="Avec --scope all : supprime aussi tous les comptes hors équipe.",
        )
        parser.add_argument(
            "--keep-phone", action="append", default=[],
            help="Avec --with-accounts : compte à conserver (répétable).",
        )
        parser.add_argument(
            "--yes", action="store_true",
            help="Applique réellement. Sans ce drapeau, rien n'est écrit.",
        )

    def handle(self, *args, **options):
        scope = options["scope"]

        if scope == "demo":
            accounts = User.objects.filter(phone__in=[*DEMO_PHONES, *options["phone"]])
            plan = self._accounts_plan(accounts, label="Comptes de démonstration")
        else:
            plan = self._everything_plan(
                extra_phones=options["phone"],
                with_accounts=options["with_accounts"],
                keep_phones=options["keep_phone"],
            )

        total = sum(count for _, count in plan["counts"])
        self.stdout.write(self.style.MIGRATE_HEADING(f"Portée : {scope}"))
        for label, count in plan["counts"]:
            self.stdout.write(f"  {label:34s} {count:6d}")
        self.stdout.write(f"  {'TOTAL':34s} {total:6d}")

        if plan["phones"]:
            shown = plan["phones"][:SHOWN_PHONES]
            more = len(plan["phones"]) - len(shown)
            self.stdout.write("\nComptes qui seraient supprimés :")
            for phone in shown:
                self.stdout.write(f"  {phone}")
            if more > 0:
                self.stdout.write(f"  … et {more} autre(s)")

        if plan["protected"]:
            self.stdout.write(
                self.style.WARNING(
                    "\nComptes d'équipe conservés : " + ", ".join(plan["protected"])
                )
            )

        if total == 0:
            self.stdout.write(self.style.SUCCESS("\nRien à supprimer."))
            return

        if not options["yes"]:
            self.stdout.write(
                self.style.NOTICE("\nSimulation : rien n'a été écrit. Ajoutez --yes pour agir.")
            )
            return

        with transaction.atomic():
            plan["execute"]()

        self.stdout.write(self.style.SUCCESS(f"\n{total} enregistrement(s) supprimé(s)."))
        self.stdout.write(
            "Les fichiers (photos, vocaux, pièces jointes) sont encore sur le disque.\n"
            "Enchaînez avec :\n"
            "    python manage.py prune_media            # pour voir\n"
            "    python manage.py prune_media --delete   # pour supprimer"
        )

    # ------------------------------------------------------------------
    def _split(self, accounts):
        """Sépare les comptes visés entre supprimables et protégés."""
        team = team_accounts()
        protected = sorted(accounts.filter(pk__in=team).values_list("phone", flat=True))
        deletable = accounts.exclude(pk__in=team)
        return deletable, protected

    def _accounts_plan(self, accounts, *, label):
        deletable, protected = self._split(accounts)

        products = Product.objects.filter(supplier__user__in=deletable)
        conversations = Conversation.objects.filter(
            Q(participant_low__in=deletable) | Q(participant_high__in=deletable)
        ).distinct()
        requests = RentalRequest.objects.filter(
            Q(client__in=deletable) | Q(product__in=products)
        ).distinct()
        # Une recherche survit au compte (le lien passe à vide) : on la
        # retire avec lui, sinon elle fausserait les statistiques.
        searches = SearchEvent.objects.filter(user__in=deletable)
        lives = LiveSession.objects.filter(host__in=deletable)

        counts = [
            (label, deletable.count()),
            ("Annonces de ces comptes", products.count()),
            ("Demandes de mise en relation", requests.count()),
            ("Conversations", conversations.count()),
            ("Directs", lives.count()),
            ("Favoris", Favorite.objects.filter(user__in=deletable).count()),
            ("Recherches", searches.count()),
            ("Notifications", Notification.objects.filter(user__in=deletable).count()),
        ]
        phones = sorted(deletable.values_list("phone", flat=True))

        def execute():
            # Les annonces d'abord : la cascade depuis le compte y arriverait
            # aussi, mais l'ordre explicite rend le décompte vérifiable.
            requests.delete()
            products.delete()
            conversations.delete()
            lives.delete()
            searches.delete()
            deletable.delete()

        return {"counts": counts, "protected": protected, "phones": phones, "execute": execute}

    def _everything_plan(self, *, extra_phones, with_accounts, keep_phones):
        if with_accounts:
            accounts = User.objects.exclude(phone__in=keep_phones)
        else:
            accounts = User.objects.filter(phone__in=extra_phones)
        deletable, protected = self._split(accounts)
        if not with_accounts and not extra_phones:
            protected = []

        counts = [
            ("Annonces", Product.objects.count()),
            ("Demandes de mise en relation", RentalRequest.objects.count()),
            ("Conversations", Conversation.objects.count()),
            ("Messages", Message.objects.count()),
            ("Directs", LiveSession.objects.count()),
            ("Favoris", Favorite.objects.count()),
            ("Vues d'annonce", ProductView.objects.count()),
            ("Contacts enregistrés", ContactEvent.objects.count()),
            ("Recherches", SearchEvent.objects.count()),
            ("Annonces importées (historique)", ListingImport.objects.count()),
            ("Notifications", Notification.objects.count()),
            ("Comptes", deletable.count()),
        ]
        phones = sorted(deletable.values_list("phone", flat=True))

        def execute():
            # Les catégories, leurs critères, les sources d'import autorisées
            # et les comptes d'équipe survivent : c'est la structure du site,
            # pas son contenu de test.
            RentalRequest.objects.all().delete()
            ListingImport.objects.all().delete()
            Product.objects.all().delete()
            Conversation.objects.all().delete()
            Message.objects.all().delete()
            LiveSession.objects.all().delete()
            Favorite.objects.all().delete()
            ProductView.objects.all().delete()
            ContactEvent.objects.all().delete()
            SearchEvent.objects.all().delete()
            Notification.objects.all().delete()
            deletable.delete()

        return {"counts": counts, "protected": protected, "phones": phones, "execute": execute}
