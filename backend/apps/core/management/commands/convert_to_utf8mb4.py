"""Passer la base MariaDB/MySQL en utf8mb4, pour qu'elle accepte les emojis.

La connexion du projet est réglée en `utf8mb4` (config/settings/cpanel.py),
mais les tables, elles, ont été créées avec le jeu de caractères par défaut
du serveur. Mesuré en production le 2026-11-17 : un message « Sonde emoji
😀 » est refusé (erreur 1366, « Incorrect string value »), le même sans
l'emoji passe. Tout texte saisi par un membre (message, annonce, demande,
nom) échouait donc dès qu'il contenait un emoji, et la notification d'une
photo, qui en commençait un, faisait répondre 500 à un envoi réussi.

Usage, sur le serveur :

    python manage.py convert_to_utf8mb4            # inventaire, ne change rien
    python manage.py convert_to_utf8mb4 --apply    # conversion

**Sauvegardez la base avant `--apply`.** La conversion réécrit chaque
table ; elle est rapide sur une petite base, mais sans retour arrière.

Sur PostgreSQL, qui stocke de l'UTF-8 complet nativement, la commande ne
fait rien.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

TARGET_CHARSET = "utf8mb4"
TARGET_COLLATION = "utf8mb4_unicode_ci"


class Command(BaseCommand):
    help = "Convertit la base et ses tables en utf8mb4 (MariaDB/MySQL seulement)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Effectuer la conversion. Sans cette option, la commande liste seulement.",
        )

    def handle(self, *args, apply=False, **options):
        if connection.vendor != "mysql":
            self.stdout.write(
                f"Base {connection.vendor} : rien à faire, l'UTF-8 complet y est natif."
            )
            return

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = DATABASE()"
            )
            db_charset, db_collation = cursor.fetchone()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            cursor.execute(
                "SELECT t.TABLE_NAME, c.CHARACTER_SET_NAME "
                "FROM information_schema.TABLES t "
                "JOIN information_schema.COLLATION_CHARACTER_SET_APPLICABILITY c "
                "  ON c.COLLATION_NAME = t.TABLE_COLLATION "
                "WHERE t.TABLE_SCHEMA = DATABASE() AND t.TABLE_TYPE = 'BASE TABLE' "
                "ORDER BY t.TABLE_NAME"
            )
            tables = cursor.fetchall()

        to_convert = [name for name, charset in tables if charset != TARGET_CHARSET]

        self.stdout.write(f"Base « {db_name} » : jeu par défaut {db_charset} ({db_collation}).")
        self.stdout.write(
            f"{len(tables)} tables, dont {len(to_convert)} à convertir en {TARGET_CHARSET}."
        )
        for name, charset in tables:
            if charset != TARGET_CHARSET:
                self.stdout.write(f"  - {name} ({charset})")

        if db_charset == TARGET_CHARSET and not to_convert:
            self.stdout.write(self.style.SUCCESS("Tout est déjà en utf8mb4. Rien à faire."))
            return

        if not apply:
            self.stdout.write(
                self.style.WARNING(
                    "Inventaire seulement. Sauvegardez la base, puis relancez avec --apply."
                )
            )
            return

        with connection.cursor() as cursor:
            # Les contraintes étrangères relient des colonnes qui doivent
            # partager le même jeu de caractères : convertir une table avant
            # l'autre échouerait sans cette suspension, levée à la fin.
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                cursor.execute(
                    f"ALTER DATABASE `{db_name}` "
                    f"CHARACTER SET {TARGET_CHARSET} COLLATE {TARGET_COLLATION}"
                )
                for index, name in enumerate(to_convert, start=1):
                    self.stdout.write(f"  [{index}/{len(to_convert)}] {name}…", ending="")
                    self.stdout.flush()
                    cursor.execute(
                        f"ALTER TABLE `{name}` "
                        f"CONVERT TO CHARACTER SET {TARGET_CHARSET} COLLATE {TARGET_COLLATION}"
                    )
                    self.stdout.write(" fait")
            except Exception as exc:
                raise CommandError(
                    f"Conversion interrompue : {exc}. Les tables déjà converties le "
                    "restent ; relancez la commande pour reprendre les autres."
                ) from exc
            finally:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        self.stdout.write(
            self.style.SUCCESS(
                f"Converti : la base et {len(to_convert)} tables sont en {TARGET_CHARSET}."
            )
        )
