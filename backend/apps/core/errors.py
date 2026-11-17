"""Dire à l'utilisateur ce qui a échoué, sans lui décrire le serveur.

Un envoi de fichier peut échouer pour des raisons qui n'ont rien à voir
avec le fichier : disque plein, quota atteint, dossier non inscriptible.
Répondre « une erreur est survenue » coûte une demi-journée de diagnostic ;
répondre le message système brut révèle des chemins et de la configuration.

Le numéro d'erreur système est le bon niveau : il distingue un disque plein
d'un dossier en lecture seule, ce qui décide de ce qu'il faut aller
corriger, et ne dit rien de la machine. Le message complet, lui, part dans
les journaux.
"""
import errno

#: Les causes qu'un exploitant peut effectivement corriger.
_SYSTEM_REASONS = {
    errno.ENOSPC: "espace disque insuffisant sur le serveur",
    errno.EDQUOT: "quota disque du compte atteint",
    errno.EACCES: "dossier des médias non inscriptible",
    errno.EPERM: "dossier des médias non inscriptible",
    errno.EROFS: "dossier des médias en lecture seule",
    errno.EMFILE: "trop de fichiers ouverts sur le serveur",
}


def storage_failure_reason(exc):
    """Une phrase courte et utile, à partir d'une exception de stockage."""
    if isinstance(exc, OSError):
        known = _SYSTEM_REASONS.get(exc.errno)
        if known:
            return known
        return f"erreur système à l'enregistrement (code {exc.errno})"
    # Le nom de la classe, pas le message : « OperationalError » ou
    # « DataError » oriente immédiatement le diagnostic sans rien révéler
    # des chemins, des requêtes ou de la configuration.
    return f"le serveur n'a pas pu enregistrer ce fichier ({type(exc).__name__})"


def is_unsupported_character(exc):
    """La base a-t-elle refusé un caractère qu'elle ne sait pas stocker ?

    MariaDB et MySQL répondent ainsi (erreur 1366, « Incorrect string
    value ») quand une table est encore en `utf8` à trois octets et qu'on
    lui donne un emoji, qui en demande quatre. La connexion du projet est
    bien en `utf8mb4` ; ce sont les tables créées avant qui ne le sont pas,
    jusqu'à `manage.py convert_to_utf8mb4`.

    Mesuré en production le 2026-11-17 : « Sonde emoji 😀 » refusé en 422,
    le même texte sans l'emoji accepté.
    """
    args = getattr(exc, "args", ()) or ()
    if args and args[0] == 1366:
        return True
    return "Incorrect string value" in str(exc)


UNSUPPORTED_CHARACTER_MESSAGE = (
    "Ce texte contient un caractère que le serveur n'accepte pas encore, "
    "un emoji par exemple. Retirez-le et réessayez."
)
