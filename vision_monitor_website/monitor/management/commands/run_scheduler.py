from django.core.management.base import BaseCommand
from monitor.openai_operations import run_scheduler
import threading
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the scheduler'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as a daemon process',
        )

    def handle(self, *args, **options):
        logger.info('Starting scheduler...')
        
        if options['daemon']:
            logger.info('Running in daemon mode')
            # Run in a separate thread
            thread = threading.Thread(target=run_scheduler)
            thread.daemon = True
            thread.start()
            logger.info('Scheduler is running in the background')
        else:
            self.stdout.write('Running in foreground mode')
            run_scheduler()
        
        logger.info('Scheduler startup complete')