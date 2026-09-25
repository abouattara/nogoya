from django.contrib import admin

from .models import Conversation, ConversationBlock, Message, MessageReport


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "participant_low", "participant_high", "initial_product", "updated_at"]
    raw_id_fields = ["participant_low", "participant_high", "initial_product"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "sender", "created_at", "read_at"]
    raw_id_fields = ["conversation", "sender", "shared_product"]


admin.site.register(ConversationBlock)
admin.site.register(MessageReport)
