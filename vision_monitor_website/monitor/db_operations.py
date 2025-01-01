import psycopg2
import logging
import asyncpg
from django.conf import settings
from psycopg2.extras import DictCursor
from django.utils import timezone

logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        return psycopg2.connect(
            host=settings.DATABASES['default']['HOST'],
            database=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            port=settings.DATABASES['default']['PORT'],
        )
    except psycopg2.Error as e:
        logger.error(f"Unable to connect to the database: {e}")
        return None

def fetch_latest_facility_state():
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT raw_message, timestamp
                FROM state_result
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            return cursor.fetchone()
    except psycopg2.Error as e:
        logger.error(f"Database error when fetching facility status: {e}")
        return None
    finally:
        conn.close()

def fetch_latest_frame_analyses():
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT ON (camera_id)
                    camera_id, camera_index, timestamp, description, camera_name
                FROM visionmon_metadata
                ORDER BY camera_id, timestamp DESC
            """)
            return cursor.fetchall()
    except psycopg2.Error as e:
        logger.error(f"Database error when fetching frame analyses: {e}")
        return None
    finally:
        conn.close()

def fetch_recent_llm_outputs(limit=50):
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT camera_id, camera_index, timestamp, description, camera_name
                FROM visionmon_metadata
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
    except psycopg2.Error as e:
        logger.error(f"Database error when fetching LLM outputs: {e}")
        return None
    finally:
        conn.close()

def insert_facility_status(raw_message, timestamp):
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO facility_status (raw_message, timestamp)
                VALUES (%s, %s)
            """, (raw_message, timestamp))
        conn.commit()
        return True
    except psycopg2.Error as e:
        logger.error(f"Database error when inserting facility status: {e}")
        return False
    finally:
        conn.close()
        
async def fetch_daily_descriptions():
    try:
        conn = await asyncpg.connect(
            host=settings.DATABASES['default']['HOST'],
            database=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD']
        )
        
        # Fetch descriptions from the last 24 hours
        query = """
        SELECT camera_name, description
        FROM visionmon_metadata
        WHERE timestamp >= NOW() - INTERVAL '1 day'
        ORDER BY timestamp DESC
        """
        
        results = await conn.fetch(query)
        
        # Format results as a dictionary
        daily_descriptions = {row['camera_name']: row['description'] for row in results}
        
        await conn.close()
        return daily_descriptions
    except Exception as e:
        print(f"Error fetching daily descriptions: {str(e)}")
        return {}
    
def get_latest_frame(camera_id):
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT vb.data
            FROM visionmon_binary_data vb
            JOIN visionmon_metadata vm ON vb.id = vm.data_id
            WHERE vm.camera_id = %s
            ORDER BY vm.timestamp DESC
            LIMIT 1
        """, (camera_id,))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching latest frame for camera {camera_id}: {str(e)}")
        return None

def fetch_timeline_events(start_time, end_time, camera_id=None):
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Database connection failed")
            return []
            
        with conn.cursor(cursor_factory=DictCursor) as cur:
            query = """
            SELECT 
                camera_id,
                camera_name,
                timestamp,
                data_id,
                COALESCE(description, 'No description available') as description
            FROM visionmon_metadata
            WHERE timestamp BETWEEN %s AND %s
            """
            if camera_id:
                query += " AND camera_id = %s"
                cur.execute(query, (start_time, end_time, camera_id))
            else:
                cur.execute(query, (start_time, end_time))
            
            results = cur.fetchall()
            
            formatted_results = []
            for row in results:
                # Ensure timestamp is properly formatted
                timestamp = row['timestamp']
                if timestamp:
                    formatted_timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
                else:
                    formatted_timestamp = None
                
                formatted_results.append({
                    'camera_id': row['camera_id'],
                    'camera_name': row['camera_name'],
                    'timestamp': formatted_timestamp,
                    'data_id': row['data_id'],
                    'description': row['description']
                })
            # reverse the results
            formatted_results.reverse()
            # Log a sample result for debugging
            if formatted_results:
                logger.debug(f"Sample timeline event: {formatted_results[0]}")
                
            return formatted_results
    except Exception as e:
        logger.error(f"Error fetching timeline events: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()
            
def get_frame_image_from_db(data_id):
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM visionmon_binary_data WHERE id = %s", (data_id,))
            result = cur.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error fetching frame image: {str(e)}")
        return None
    finally:
        conn.close()