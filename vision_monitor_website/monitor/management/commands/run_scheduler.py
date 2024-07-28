from django.core.management.base import BaseCommand
from monitor.openai_operations import run_scheduler

class Command(BaseCommand):
    help = 'Runs the scheduler'

    def handle(self, *args, **options):
        self.stdout.write('Starting scheduler...')
        run_scheduler()
        self.stdout.write('Scheduler is running')