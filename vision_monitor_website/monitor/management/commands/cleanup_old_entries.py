# File: monitor/management/commands/cleanup_old_entries.py

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Deletes frame analysis entries older than 30 days'

    def handle(self, *args, **options):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH old_metadata AS (
                    SELECT id, data_id 
                    FROM visionmon_metadata 
                    WHERE timestamp < %s
                ),
                deleted_metadata AS (
                    DELETE FROM visionmon_metadata
                    WHERE id IN (SELECT id FROM old_metadata)
                    RETURNING id
                ),
                deleted_binary_data AS (
                    DELETE FROM visionmon_binary_data
                    WHERE id IN (SELECT data_id FROM old_metadata)
                    RETURNING id
                ),
                old_state_results AS (
                    SELECT id
                    FROM state_result 
                    WHERE timestamp < %s
                ),
                deleted_state_results AS (
                    DELETE FROM state_result
                    WHERE id IN (SELECT id FROM old_state_results)
                    RETURNING id
                )
                SELECT 
                    (SELECT COUNT(*) FROM deleted_metadata) +
                    (SELECT COUNT(*) FROM deleted_binary_data) +
                    (SELECT COUNT(*) FROM deleted_state_results) as total_deleted;
            """, [thirty_days_ago, thirty_days_ago])
            
            deleted_count = cursor.fetchone()[0]

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted entries older than {thirty_days_ago}. Affected rows: {deleted_count}'))