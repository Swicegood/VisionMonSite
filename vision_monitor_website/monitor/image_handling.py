import logging
from django.http import HttpResponse, Http404
import redis
import base64
from .db_operations import get_db_connection, get_frame_image_from_db

logger = logging.getLogger(__name__)

redis_client = redis.Redis(host='192.168.0.71', port=6379)

def get_latest_image(request, camera_index):
    conn = get_db_connection()
    if not conn:
        raise Http404("Database connection failed")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT vb.data, vm.timestamp
                FROM visionmon_metadata vm
                JOIN visionmon_binary_data vb ON vm.data_id = vb.id
                WHERE vm.camera_index = %s
                ORDER BY vm.timestamp DESC
                LIMIT 1
            """, [camera_index])
            result = cursor.fetchone()
            if result:
                image_data, timestamp = result
                response = HttpResponse(image_data, content_type='image/jpeg')
                
                response['Cache-Control'] = 'no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                
                response['X-Image-Timestamp'] = timestamp.isoformat()
                
                return response
            else:
                raise Http404("Image not found")
    except Exception as e:
        logger.error(f"Error retrieving latest image: {str(e)}")
        raise Http404("Error retrieving image")
    finally:
        conn.close()
        
def get_latest_image_non_web(camera_index):
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT vb.data, vm.timestamp
                FROM visionmon_metadata vm
                JOIN visionmon_binary_data vb ON vm.data_id = vb.id
                WHERE vm.camera_index = %s
                ORDER BY vm.timestamp DESC
                LIMIT 1
            """, [camera_index])
            result = cursor.fetchone()
            if result:
                image_data, timestamp = result
                return image_data, timestamp
            else:
                logger.error("Image not found")
    except Exception as e:
        logger.error(f"Error retrieving latest image: {str(e)}")
    finally:
        conn.close()

def get_composite_image(request, camera_name):
    composite_key = f'composite_{camera_name}'
    composite_data = redis_client.get(composite_key)
    if composite_data:
        return HttpResponse(composite_data, content_type='image/png')
    else:
        return HttpResponse(status=404)

def get_composite_images(latest_frame_analyses):
    composite_images = {}
    for analysis in latest_frame_analyses:
        camera_id = analysis[0]
        composite_key = f'composite_{camera_id}'
        composite_data = redis_client.get(composite_key)
        if composite_data:
            composite_images[camera_id] = base64.b64encode(composite_data).decode('utf-8')
    return composite_images

def get_frame_image(request, data_id):
    image_data = get_frame_image_from_db(data_id)
    if image_data:
        return HttpResponse(image_data, content_type='image/jpeg')
    else:
        return HttpResponse(status=404)