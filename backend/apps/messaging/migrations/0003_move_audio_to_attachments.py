"""Move existing voice notes onto `media.MessageAttachment`.

Runs before the columns are dropped, so no recording is lost. The bytes are
not copied: the attachment points at the key the file already occupies
(`messages/audio/…`). New uploads land under `chat/…`; both coexist, and the
old prefix empties itself as conversations age.
"""
from django.db import migrations

EXTENSION_MIME = {
    "webm": "audio/webm",
    "ogg": "audio/ogg",
    "oga": "audio/ogg",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "mp4": "audio/mp4",
    "aac": "audio/aac",
}


def forwards(apps, schema_editor):
    Message = apps.get_model("messaging", "Message")
    Attachment = apps.get_model("nogoya_media", "MessageAttachment")

    rows = []
    for message in Message.objects.exclude(audio_file="").exclude(audio_file=None).iterator():
        name = message.audio_file.name
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else "webm"
        rows.append(
            Attachment(
                message_id=message.pk,
                kind="audio",
                status="ready",
                file=name,
                mime_type=EXTENSION_MIME.get(extension, "audio/webm"),
                duration=message.audio_duration or 0,
                position=0,
            )
        )
    Attachment.objects.bulk_create(rows, batch_size=200)


def backwards(apps, schema_editor):
    Message = apps.get_model("messaging", "Message")
    Attachment = apps.get_model("nogoya_media", "MessageAttachment")
    for attachment in Attachment.objects.filter(kind="audio").iterator():
        Message.objects.filter(pk=attachment.message_id).update(
            audio_file=attachment.file.name, audio_duration=attachment.duration
        )
    Attachment.objects.filter(kind="audio").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0002_message_audio_duration_message_audio_file_and_more"),
        ("nogoya_media", "0001_chat_attachments"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
