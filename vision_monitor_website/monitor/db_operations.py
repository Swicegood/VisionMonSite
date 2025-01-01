import psycopg2
import logging
import asyncpg
from django.conf import settings
from psycopg2.extras import DictCursor
from django.utils import timezone
import json

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
                vm.camera_id,
                vm.camera_name,
                vm.timestamp,
                vm.data_id,
                COALESCE(vm.description, 'No description available') as description,
                (
                    SELECT raw_message
                    FROM state_result sr
                    WHERE sr.timestamp <= vm.timestamp
                    ORDER BY sr.timestamp DESC
                    LIMIT 1
                ) as state_data
            FROM visionmon_metadata vm
            WHERE vm.timestamp BETWEEN %s AND %s
            """
            if camera_id:
                query += " AND vm.camera_id = %s"
                cur.execute(query, (start_time, end_time, camera_id))
            else:
                cur.execute(query, (start_time, end_time))
            
            results = cur.fetchall()
            
            formatted_results = []
            for row in results:
                timestamp = row['timestamp']
                formatted_timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f%z') if timestamp else None
                
                # Parse the state data JSON to get camera states
                state_data = json.loads(row['state_data']) if row['state_data'] else {}
                camera_states = state_data.get('camera_states', {})
                # Match camera name ignoring the number suffix
                camera_state = ''
                source_name = str(row['camera_name']).split(' ')[0]  # Get name part without number
                for target_name, state in camera_states.items():
                    target_base = target_name.split(' ')[0]  # Get base name without number
                    if source_name == target_base:
                        camera_state = state
                        break
                print(f"Camera state: {camera_state}")
                formatted_results.append({
                    'camera_id': row['camera_id'],
                    'camera_name': row['camera_name'],
                    'timestamp': formatted_timestamp,
                    'data_id': row['data_id'],
                    'description': row['description'],
                    'state': camera_state
                })
            
            formatted_results.reverse()
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