from django.core.management.base import BaseCommand

from scheduling.demo import get_demo_user_matrix, seed_demo_environment


class Command(BaseCommand):
    help = 'Seed a repeatable local demo environment with fake users, schedule, bookings, and recoveries.'

    def handle(self, *args, **options):
        summary = seed_demo_environment()

        self.stdout.write(self.style.SUCCESS('Demo ready: fake local data seeded successfully.'))
        self.stdout.write(
            (
                f'- sections ensured={summary.sections_ensured} '
                f'(created={summary.sections_created})'
            )
        )
        self.stdout.write(f'- demo slots created={summary.demo_slots_created}')
        self.stdout.write(f'- future sessions generated={summary.sessions_generated}')
        self.stdout.write(f'- demo students seeded={summary.students_seeded}')
        self.stdout.write(f'- demo bookings created={summary.bookings_created}')
        self.stdout.write(f'- demo recoveries created={summary.recoveries_created}')
        self.stdout.write('- demo users:')
        for user in get_demo_user_matrix():
            self.stdout.write(
                f'  - {user["role"]}: {user["email"]} / {user["password"]} - {user["description"]}'
            )
