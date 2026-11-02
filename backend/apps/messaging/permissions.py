from rest_framework import permissions


class IsConversationParticipant(permissions.BasePermission):
    """Le membre du fil — ou l'équipe, qui répond dans tous les fils.

    Depuis le schéma intermédié, l'équipe n'est pas « participante » au sens
    de la paire stockée : c'est le compte de service NOGOYA qui occupe ce
    côté. Sans cette exception, un membre de l'équipe se voyait refuser
    l'envoi d'un message dans le fil qu'il est pourtant chargé de traiter.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated and request.user.is_staff:
            return True
        return obj.has_participant(request.user)
