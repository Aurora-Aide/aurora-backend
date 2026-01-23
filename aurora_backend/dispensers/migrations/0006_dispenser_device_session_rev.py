from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dispensers', '0005_fill_device_secret'),
    ]

    operations = [
        migrations.AddField(
            model_name='dispenser',
            name='device_session_rev',
            field=models.PositiveIntegerField(default=1),
        ),
    ]

