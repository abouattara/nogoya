from rest_framework import permissions


class IsConversationParticipant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.has_participant(request.user)
