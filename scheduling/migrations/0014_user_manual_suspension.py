from django.db import migrations, models


def preserve_existing_inactive_users_as_manual(apps, schema_editor):
    User = apps.get_model('scheduling', 'User')
    User.objects.filter(is_active=False).update(manual_suspension=True)


class Migration(migrations.Migration):
    dependencies = [('scheduling', '0013_passwordresetratelimit')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='manual_suspension',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(preserve_existing_inactive_users_as_manual, migrations.RunPython.noop),
    ]
