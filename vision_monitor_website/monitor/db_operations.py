import psycopg2
import logging
from django.conf import settings

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