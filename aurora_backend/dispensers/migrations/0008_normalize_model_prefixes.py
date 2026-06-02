from django.db import migrations


def _normalize(value):
    return (value or "").strip().upper().rstrip("-")


def normalize_model_prefixes(apps, schema_editor):
    DispenserModel = apps.get_model("dispensers", "DispenserModel")
    Dispenser = apps.get_model("dispensers", "Dispenser")

    # First pass: normalize code/serial_prefix and merge duplicate normalized codes.
    keepers_by_code = {}
    for model in DispenserModel.objects.all().order_by("id"):
        normalized_code = _normalize(model.code)
        normalized_prefix = _normalize(model.serial_prefix) or normalized_code
        if not normalized_code:
            continue

        keeper = keepers_by_code.get(normalized_code)
        if keeper is None:
            model.code = normalized_code
            model.serial_prefix = normalized_prefix
            model.save(update_fields=["code", "serial_prefix"])
            keepers_by_code[normalized_code] = model
            continue

        Dispenser.objects.filter(dispenser_model_id=model.id).update(dispenser_model_id=keeper.id)
        model.delete()

    # Second pass: ensure serial_prefix remains unique after normalization.
    used_prefixes = set()
    for model in DispenserModel.objects.all().order_by("id"):
        base_prefix = _normalize(model.serial_prefix) or _normalize(model.code)
        if not base_prefix:
            base_prefix = f"MODEL{model.id}"

        candidate = base_prefix
        suffix = 2
        while candidate in used_prefixes:
            candidate = f"{base_prefix}{suffix}"
            suffix += 1

        if model.serial_prefix != candidate:
            model.serial_prefix = candidate
            model.save(update_fields=["serial_prefix"])
        used_prefixes.add(candidate)

    # Normalize legacy size values like "S-" to "S".
    for dispenser in Dispenser.objects.all().only("id", "size"):
        normalized_size = _normalize(dispenser.size)
        if normalized_size and normalized_size != dispenser.size:
            dispenser.size = normalized_size
            dispenser.save(update_fields=["size"])


class Migration(migrations.Migration):

    dependencies = [
        ("dispensers", "0007_mobilepushtoken"),
    ]

    operations = [
        migrations.RunPython(normalize_model_prefixes, migrations.RunPython.noop),
    ]
