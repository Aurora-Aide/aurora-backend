from django.db import migrations
import secrets


def populate_device_secret(apps, schema_editor):
    Dispenser = apps.get_model("dispensers", "Dispenser")
    for dispenser in Dispenser.objects.filter(device_secret=""):
        dispenser.device_secret = secrets.token_hex(16)
        dispenser.save(update_fields=["device_secret"])


class Migration(migrations.Migration):
    dependencies = [
        ("dispensers", "0004_scheduleevent"),
    ]

    operations = [
        migrations.RunPython(populate_device_secret, migrations.RunPython.noop),
    ]


