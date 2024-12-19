# File: monitor/management/commands/cleanup_old_entries.py

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from datetime import timedelta
import logging

class Command(BaseCommand):
    help = 'Deletes frame analysis entries older than 30 days'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting cleanup operation...'))
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        self.stdout.write(f'Will delete entries older than: {thirty_days_ago}')
        
        try:
            with connection.cursor() as cursor:
                self.stdout.write('Executing deletion query...')
                cursor.execute("""
                    EXPLAIN ANALYZE
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
                
                query_plan = cursor.fetchall()
                self.stdout.write('Query plan:')
                for row in query_plan:
                    self.stdout.write(f'    {row[0]}')
                
                # Execute the actual deletion query without EXPLAIN ANALYZE
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
                self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} entries'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during cleanup: {str(e)}'))
            # Get details about any blocking queries
            cursor.execute("""
                SELECT pid, state, query_start, query
                FROM pg_stat_activity
                WHERE state != 'idle';
            """)
            active_queries = cursor.fetchall()
            self.stdout.write('Active database queries:')
            for query in active_queries:
                self.stdout.write(f'    PID: {query[0]}, State: {query[1]}, Started: {query[2]}')
                self.stdout.write(f'    Query: {query[3]}')
            raise

        self.stdout.write(self.style.SUCCESS('Cleanup operation completed'))