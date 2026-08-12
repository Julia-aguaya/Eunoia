from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('scheduling', '0011_fixedbookingcapacityconflict')]

    operations = [
        migrations.AddField(
            model_name='studentmonthlyplan',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
