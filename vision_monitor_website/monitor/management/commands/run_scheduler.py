# monitor/management/commands/run_scheduler.py

from django.core.management.base import BaseCommand
from monitor.openai_operations import run_scheduler
from monitor.scheduled_tasks import run_no_show_checks, run_cleanup_old_entries
import threading
import asyncio
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the scheduler and no-show checks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as a daemon process',
        )

    def handle(self, *args, **options):
        logger.info('Starting scheduler and no-show checks...')
        
        if options['daemon']:
            logger.info('Running in daemon mode')
            # Run scheduler in a separate thread
            scheduler_thread = threading.Thread(target=run_scheduler)
            scheduler_thread.daemon = True
            scheduler_thread.start()

            # Run no-show checks in the main thread
            asyncio.run(run_no_show_checks())
            # Run cleanup operation in the main thread
            asyncio.run(run_cleanup_old_entries())
        else:
            self.stdout.write('Running in foreground mode')
            # Run scheduler in a separate thread
            scheduler_thread = threading.Thread(target=run_scheduler)
            scheduler_thread.start()

            # Run no-show checks in the main thread
            asyncio.run(run_no_show_checks())
            # Run cleanup operation in the main thread
            asyncio.run(run_cleanup_old_entries())
        
        logger.info('Finished scheduler and no-show checks and cleanup operation')

    def run_both(self):
        # This method is used for the non-daemon mode
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.start()
        
        asyncio.run(run_no_show_checks())
        asyncio.run(run_cleanup_old_entries())