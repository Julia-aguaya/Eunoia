from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0006_studentmonthlyplan_studentmonthlyplanslot_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='studentmonthlyplan',
            name='unique_student_monthly_plan_per_month',
        ),
        migrations.AddConstraint(
            model_name='studentmonthlyplan',
            constraint=models.UniqueConstraint(
                fields=('student', 'month', 'section'),
                name='unique_student_monthly_plan_per_month_section',
            ),
        ),
    ]
