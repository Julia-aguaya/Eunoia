# Generated manually for the fixed-booking capacity conflict read model.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [('scheduling', '0010_user_monthly_plan_reset_from')]

    operations = [
        migrations.CreateModel(
            name='FixedBookingCapacityConflict',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('state', models.CharField(choices=[('pending', 'Pending'), ('resolved', 'Resolved')], default='pending', max_length=16)),
                ('first_detected_at', models.DateTimeField(auto_now_add=True)),
                ('last_detected_at', models.DateTimeField(auto_now=True)),
                ('capacity', models.PositiveIntegerField()),
                ('active_booking_count', models.PositiveIntegerField()),
                ('expected_fixed_student_ids', models.JSONField(default=list)),
                ('active_booking_snapshot', models.JSONField(default=list)),
                ('detail', models.TextField(blank=True)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='fixed_capacity_conflict', to='scheduling.classsession')),
            ],
            options={'ordering': ['state', '-last_detected_at']},
        ),
    ]
