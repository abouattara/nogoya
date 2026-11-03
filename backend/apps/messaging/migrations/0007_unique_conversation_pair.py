"""La contrainte, dans sa propre transaction.

PostgreSQL refuse un `ALTER TABLE` dans la meme transaction que des
ecritures sur cette table : « ne peut pas executer ALTER TABLE car il reste
des evenements sur les triggers ». La fusion des fils en double vit donc
dans la migration precedente, et la contrainte ici.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0006_remove_conversation_unique_thread_per_pair_and_product_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="conversation",
            constraint=models.UniqueConstraint(
                fields=("participant_low", "participant_high"),
                name="unique_conversation_pair",
            ),
        ),
    ]
