import redis
import logging
import time
from .config import REDIS_HOST, REDIS_PORT

logger = logging.getLogger(__name__)

class CustomTimeoutError(redis.TimeoutError, TimeoutError):
    pass

def connect_redis(max_retries=5, retry_delay=5):
    for attempt in range(max_retries):
        try:
            redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                socket_timeout=10,  # Set a timeout for operations
                socket_connect_timeout=10  # Set a timeout for connection
            )
            # Test the connection
            redis_client.ping()
            logger.info("Connected to Redis")
            return redis_client
        except (redis.TimeoutError, redis.ConnectionError) as e:
            logger.error(f"Failed to connect to Redis (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Unexpected error while connecting to Redis: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    raise CustomTimeoutError("Max retries reached. Could not connect to Redis.")

def main():
    try:
        redis_client = connect_redis()
        # Use redis_client here
        # For example:
        redis_client.set('test_key', 'test_value')
        value = redis_client.get('test_key')
        print(f"Retrieved value: {value}")
    except CustomTimeoutError as e:
        logger.error(f"Timed out while trying to connect to Redis: {e}")
    except redis.RedisError as e:
        logger.error(f"Redis error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        if 'redis_client' in locals() and redis_client is not None:
            redis_client.close()

if __name__ == "__main__":
    main()