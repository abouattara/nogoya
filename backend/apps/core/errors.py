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
