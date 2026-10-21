"""Le stockage des médias accepte-t-il une écriture, ici et maintenant ?

Un envoi de photo qui échoue en 500 pose toujours la même question, et y
répondre en lisant des journaux prend dix minutes. Cette commande y répond
en une : elle écrit réellement un fichier par le stockage configuré, le
relit, et le supprime.

    python manage.py check_media

Elle ne modifie rien de durable, et sort en code 1 si l'écriture échoue —
de quoi la mettre dans une surveillance si besoin.
"""
import errno
import os
import shutil
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

DIAGNOSES = {
    errno.ENOSPC: "le disque est plein",
    errno.EDQUOT: "le quota disque du compte est atteint",
    errno.EACCES: "le dossier n'est pas inscriptible par l'utilisateur qui exécute l'application",
    errno.EPERM: "le dossier n'est pas inscriptible par l'utilisateur qui exécute l'application",
    errno.EROFS: "le système de fichiers est monté en lecture seule",
    errno.EMFILE: "trop de fichiers ouverts sur le serveur",
}


class Command(BaseCommand):
    help = "Vérifie que le stockage des médias accepte une écriture."

    def handle(self, *args, **options):
        storage = default_storage
        self.stdout.write(f"Stockage      : {storage.__class__.__name__}")
        root = getattr(settings, "MEDIA_ROOT", None)
        self.stdout.write(f"MEDIA_ROOT    : {root}")

        if root:
            self.stdout.write(f"  existe      : {os.path.isdir(root)}")
            self.stdout.write(f"  inscriptible: {os.access(root, os.W_OK)} (selon os.access)")
            try:
                usage = shutil.disk_usage(root if os.path.isdir(root) else ".")
                libre = usage.free / 1024 / 1024 / 1024
                pris = 100 * (usage.used / usage.total)
                self.stdout.write(f"  disque      : {libre:.1f} Gio libres, {pris:.0f} % occupé")
            except OSError as exc:
                self.stdout.write(f"  disque      : indisponible ({exc})")

        # Le seul test qui compte : écrire pour de bon, par le même chemin
        # que l'application. `os.access` ment sur certains montages, et ne
        # dit rien d'un quota.
        name = f"diagnostic/{uuid.uuid4().hex}.txt"
        try:
            written = storage.save(name, ContentFile(b"nogoya check_media"))
        except OSError as exc:
            cause = DIAGNOSES.get(exc.errno, f"code système {exc.errno}")
            self.stderr.write(self.style.ERROR(f"\nÉCRITURE REFUSÉE : {cause}"))
            self.stderr.write(f"  {exc}")
            raise SystemExit(1)
        except Exception as exc:  # stockage objet, permissions S3, etc.
            self.stderr.write(self.style.ERROR(f"\nÉCRITURE REFUSÉE : {type(exc).__name__}"))
            self.stderr.write(f"  {exc}")
            raise SystemExit(1)

        try:
            with storage.open(written) as handle:
                relu = handle.read()
            ok = relu == b"nogoya check_media"
        finally:
            storage.delete(written)

        if not ok:
            self.stderr.write(self.style.ERROR("\nÉcriture acceptée mais relecture incorrecte."))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("\nÉcriture, relecture et suppression : OK."))
        self.stdout.write("Le stockage n'est pas en cause dans un échec d'envoi de photo.")
