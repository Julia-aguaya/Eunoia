from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('scheduling', '0014_user_manual_suspension')]

    operations = [
        migrations.AlterField(
            model_name='monthlyaccessstatus',
            name='booking_enabled',
            field=models.BooleanField(default=True),
        ),
    ]
