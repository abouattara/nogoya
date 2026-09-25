"""Drop the audio columns, now that 0003 has copied them to attachments."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0003_move_audio_to_attachments'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='audio_duration',
        ),
        migrations.RemoveField(
            model_name='message',
            name='audio_file',
        ),
        migrations.AlterField(
            model_name='message',
            name='message_type',
            field=models.CharField(choices=[('text', 'Texte'), ('audio', 'Audio'), ('image', 'Image'), ('video', 'Vidéo'), ('product', 'Annonce'), ('system', 'Système')], default='text', max_length=12, verbose_name='type'),
        ),
    ]
