"""Find and remove media that no row points to any more.

Two things leave files behind that the delete signals cannot catch:

* an upload that was stored and then failed to commit (a crash, a rollback
  in the middle of a multi-file message);
* files written by an older version of the code, under a prefix nothing
  references now.

This walks the storage prefixes we own, compares what is there with what the
database knows, and deletes the difference. It is deliberately a command and
not a background job: deleting files is the kind of thing an operator should
be able to preview first.

    python manage.py prune_media            # report only
    python manage.py prune_media --delete   # actually remove them
"""
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db.models import FileField
from django.utils import timezone

# Prefixes this project writes to. Anything else in the bucket is not ours
# to delete.
PREFIXES = ("chat", "messages", "products", "avatars", "live")


def _walk(prefix):
    """Every file under a prefix, depth-first. Works on any storage backend."""
    try:
        directories, files = default_storage.listdir(prefix)
    except (FileNotFoundError, NotImplementedError, OSError):
        return
    for name in files:
        yield f"{prefix}/{name}"
    for directory in directories:
        yield from _walk(f"{prefix}/{directory}")


def referenced_keys():
    """Every storage key the database still points at.

    Found by walking the models rather than by listing the ones we remember:
    a file field added later and forgotten here would make this command
    delete live files. The introspection is the safety property.
    """
    keys = set()
    for model in apps.get_models():
        names = [f.name for f in model._meta.get_fields() if isinstance(f, FileField)]
        if not names:
            continue
        for row in model._default_manager.values_list(*names):
            keys.update(value for value in row if value)
    return keys


class Command(BaseCommand):
    help = "Report (or delete) stored files that no database row references."

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete", action="store_true", help="Actually remove the orphans."
        )
        parser.add_argument(
            "--hours",
            type=int,
            default=None,
            help=(
                "Only consider files older than this many hours "
                f"(default: ORPHAN_MEDIA_RETENTION_HOURS = {settings.ORPHAN_MEDIA_RETENTION_HOURS})."
            ),
        )

    def handle(self, *args, **options):
        verbose = options.get("verbosity", 1) > 0
        hours = options["hours"]
        if hours is None:
            hours = settings.ORPHAN_MEDIA_RETENTION_HOURS
        cutoff = timezone.now() - timedelta(hours=hours)

        keys = referenced_keys()
        orphans, freed, skipped_recent = [], 0, 0

        for prefix in PREFIXES:
            for key in _walk(prefix):
                if key in keys:
                    continue
                # A file uploaded seconds ago may belong to a request that is
                # still running: deleting it would break a message as it is
                # being written.
                try:
                    if default_storage.get_created_time(key) > cutoff:
                        skipped_recent += 1
                        continue
                    size = default_storage.size(key)
                except (NotImplementedError, OSError):
                    size = 0
                orphans.append(key)
                freed += size

        for key in orphans:
            if verbose:
                self.stdout.write(f"  orphelin : {key}")
            if options["delete"]:
                try:
                    default_storage.delete(key)
                except OSError as exc:
                    self.stderr.write(f"    suppression impossible : {exc}")

        verb = "supprimés" if options["delete"] else "à supprimer (--delete pour agir)"
        if not verbose:
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(orphans)} fichier(s) {verb}, {freed / 1024 / 1024:.1f} Mo — "
                f"{skipped_recent} fichier(s) récent(s) ignoré(s), "
                f"{len(keys)} référencé(s) en base."
            )
        )
