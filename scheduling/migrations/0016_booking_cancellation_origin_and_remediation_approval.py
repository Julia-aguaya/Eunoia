from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('scheduling', '0015_alter_monthlyaccessstatus_booking_enabled')]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='cancellation_origin',
            field=models.CharField(
                blank=True,
                choices=[
                    ('automatic_access_impact', 'Automatic Access Impact'),
                    ('student_self_service', 'Student Self-Service'),
                    ('staff_manual', 'Staff Manual'),
                    ('session_cancellation', 'Session Cancellation'),
                ],
                max_length=32,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='classsession',
            name='cancellation_origin',
            field=models.CharField(
                blank=True,
                choices=[
                    ('automatic_access_impact', 'Automatic Access Impact'),
                    ('student_self_service', 'Student Self-Service'),
                    ('staff_manual', 'Staff Manual'),
                    ('session_cancellation', 'Session Cancellation'),
                ],
                max_length=32,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name='BookingRemediationApproval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approved_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('notes', models.TextField()),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_booking_remediations', to=settings.AUTH_USER_MODEL)),
                ('booking', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='remediation_approval', to='scheduling.booking')),
            ],
            options={'ordering': ['-approved_at', '-pk']},
        ),
    ]
