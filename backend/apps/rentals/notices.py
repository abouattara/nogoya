"""Donner au fil le contexte de la demande.

Sans cela, l'équipe ouvrait une conversation **vide**. Le client avait
rempli des dates et un message, et rien de tout cela n'apparaissait : il
fallait aller chercher la demande ailleurs pour savoir de quoi on parlait.

Un message de service résume donc la demande à sa création. Il est marqué
`SYSTEM` : ce n'est pas le client qui parle, et il ne doit pas compter comme
un message non lu à traiter — c'est le récapitulatif qui ouvre le dossier.
"""
import logging

from apps.messaging.models import Message

logger = logging.getLogger("nogoya.rentals")


def describe_period(demande):
    """« du 12 au 16 novembre » ou « à partir du 12 novembre, durée indéterminée »."""
    debut = f"{demande.start_date:%d/%m/%Y}"
    if demande.end_date is None:
        return f"à partir du {debut}, durée indéterminée"
    return f"du {debut} au {demande.end_date:%d/%m/%Y} ({demande.nights} jour(s))"


def summarise(demande):
    """Le texte du récapitulatif, lisible tel quel dans le fil."""
    lignes = [
        "Demande de location",
        f"Période : {describe_period(demande)}",
        f"Demandeur : {demande.requester_label} ({demande.requester_phone or 'sans numéro'})",
    ]
    if demande.message:
        lignes.append(f"Message : {demande.message}")
    lignes.append("")
    lignes.append(
        "À faire : vérifier la disponibilité auprès du fournisseur, "
        "puis transmettre les coordonnées si le bien est libre."
    )
    return "\n".join(lignes)


def announce_request(demande):
    """Écrit le récapitulatif dans le fil, s'il y en a un.

    Ne lève jamais : une demande enregistrée ne doit pas échouer parce que
    son résumé n'a pas pu s'écrire. Le pire cas reste l'ancien — un fil
    sans contexte — et il est journalisé.
    """
    if demande.thread_id is None:
        return None
    try:
        return Message.objects.create(
            conversation=demande.thread,
            sender=demande.client,
            message_type=Message.Type.SYSTEM,
            body=summarise(demande),
            # L'annonce est jointe au message, pas seulement nommée dans le
            # texte : le fil affiche alors sa carte, cliquable, avec sa
            # photo et son prix. Lire « Demande de location — Moto » sans
            # pouvoir ouvrir l'annonce obligeait à la chercher à la main.
            shared_product=demande.product,
            # Lu d'emblée : c'est un récapitulatif, pas une question en
            # attente. Le compter comme non lu gonflerait le badge de
            # l'équipe sans rien lui apprendre de plus que la file.
            read_at=demande.created_at,
        )
    except Exception:
        logger.exception("Récapitulatif non écrit pour la demande %s", demande.pk)
        return None
