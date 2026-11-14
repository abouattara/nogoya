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
    # Pas de titre ici : le fil encadre la note et l'intitule lui-meme.
    # Le repeter donnait « Demande de location / Demande de location ».
    lignes = [
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


def supplier_contact(demande):
    """Les coordonnées du fournisseur de ce bien, telles qu'on les transmet.

    Le WhatsApp ne sort que si le fournisseur l'a autorisé : c'est sa
    décision, pas la nôtre. Le nom est le nom public, jamais le numéro
    déguisé en nom.
    """
    profile = demande.product.supplier
    user = profile.user
    whatsapp = profile.whatsapp_number if profile.allow_whatsapp_contact else ""
    return {
        "name": user.public_name("Fournisseur"),
        "phone": user.phone or "",
        "whatsapp": whatsapp or "",
    }


def describe_contact(demande, contact):
    """Le texte que le client lit au moment de la mise en relation."""
    lignes = [
        f"Bonne nouvelle : « {demande.product.title} » est disponible "
        f"{describe_period(demande)}.",
        "",
        "Voici les coordonnées du fournisseur :",
        f"• {contact['name']}",
    ]
    if contact["phone"]:
        lignes.append(f"• Téléphone : {contact['phone']}")
    if contact["whatsapp"] and contact["whatsapp"] != contact["phone"]:
        lignes.append(f"• WhatsApp : {contact['whatsapp']}")
    elif contact["whatsapp"]:
        lignes.append("• Joignable aussi sur WhatsApp à ce numéro")
    lignes += [
        "",
        "Convenez directement avec lui du prix, de la caution et de la remise "
        "du bien. Constatez son état ensemble, photos à l'appui. En cas de "
        "souci, écrivez-nous ici.",
    ]
    return "\n".join(lignes)


def announce_contact(demande, sender):
    """Écrit les coordonnées du fournisseur dans le fil du client.

    C'est le moment que tout le parcours prépare, et il ne produisait
    rien : la demande passait « mise en relation faite », mais aucun
    message ne partait. Le client n'avait aucun moyen de joindre le
    fournisseur, et l'équipe ne voyait pas le numéro pour le lui relayer.

    Le message part au nom de NOGOYA, pas comme note de service : c'est
    l'équipe qui parle au client, et il doit compter comme non lu pour
    que la pastille l'avertisse. Une notification l'accompagne.

    Un visiteur sans compte n'a pas de fil : rien ne s'écrit, et c'est à
    l'équipe de l'appeler, numéro du fournisseur sous les yeux.

    Ne lève jamais : la mise en relation est enregistrée, c'est elle qui
    fait foi. Un message manqué se rattrape, une décision perdue non.
    """
    from apps.messaging.services import support_account
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    if demande.thread_id is None:
        return None
    try:
        contact = supplier_contact(demande)
        message = Message.objects.create(
            conversation=demande.thread,
            sender=support_account(),
            staff_author=sender if getattr(sender, "is_staff", False) else None,
            message_type=Message.Type.TEXT,
            body=describe_contact(demande, contact),
            shared_product=demande.product,
        )
        demande.thread.save(update_fields=["updated_at"])
        notify(
            demande.client,
            type=Notification.Type.NEW_MESSAGE,
            title="Votre demande est acceptée",
            message=(
                f"« {demande.product.title} » est disponible. Les coordonnées "
                "du fournisseur sont dans votre messagerie."
            ),
            url=f"/compte/messages/{demande.thread_id}",
            data={"conversation_id": demande.thread_id, "rental_request_id": demande.pk},
        )
        return message
    except Exception:
        logger.exception("Coordonnées non transmises dans le fil, demande %s", demande.pk)
        return None
