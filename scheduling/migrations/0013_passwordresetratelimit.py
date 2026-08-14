from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('scheduling', '0012_studentmonthlyplan_is_active')]

    operations = [
        migrations.CreateModel(
            name='PasswordResetRateLimit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scope', models.CharField(max_length=10)),
                ('principal_digest', models.CharField(max_length=64)),
                ('window_started_at', models.DateTimeField()),
                ('count', models.PositiveSmallIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=('scope', 'principal_digest'), name='password_reset_rate_limit_principal'),
                ],
            },
        ),
    ]
