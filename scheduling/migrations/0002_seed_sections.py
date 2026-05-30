from django.db import migrations


def seed_sections(apps, schema_editor):
    Section = apps.get_model('scheduling', 'Section')

    sections = [
        ('reformer_arriba', 'Reformer Arriba'),
        ('reformer_abajo', 'Reformer Abajo'),
        ('cadillac', 'Cadillac'),
    ]

    for code, name in sections:
        Section.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'default_capacity': 7,
                'is_active': True,
            },
        )


def unseed_sections(apps, schema_editor):
    Section = apps.get_model('scheduling', 'Section')
    Section.objects.filter(code__in=['reformer_arriba', 'reformer_abajo', 'cadillac']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('scheduling', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_sections, unseed_sections),
    ]
