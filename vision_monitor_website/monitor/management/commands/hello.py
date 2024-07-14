from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Prints Hello, World!'

    def handle(self, *args, **options):
        self.stdout.write('Hello, World!')