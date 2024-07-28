from django.core.management.base import BaseCommand
from monitor.openai_operations import run_scheduler
import threading

class Command(BaseCommand):
    help = 'Runs the scheduler'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as a daemon process',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting scheduler...')
        
        if options['daemon']:
            self.stdout.write('Running in daemon mode')
            # Run in a separate thread
            thread = threading.Thread(target=run_scheduler)
            thread.daemon = True
            thread.start()
            self.stdout.write('Scheduler is running in the background')
        else:
            self.stdout.write('Running in foreground mode')
            run_scheduler()
        
        self.stdout.write('Scheduler startup complete')