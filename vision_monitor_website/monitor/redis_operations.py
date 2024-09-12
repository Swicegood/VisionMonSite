import asyncio
import aioredis
import logging
from config import REDIS_HOST, REDIS_PORT

logger = logging.getLogger(__name__)

# Custom TimeoutError class
class CustomTimeoutError(asyncio.TimeoutError, aioredis.RedisError):
    pass

async def connect_redis():
    while True:
        try:
            redis_client = await aioredis.create_redis_pool(
                f'redis://{REDIS_HOST}:{REDIS_PORT}',
                timeout=10  # Add a timeout for the connection attempt
            )
            logger.info("Connected to Redis")
            return redis_client
        except (aioredis.RedisError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error while connecting to Redis: {str(e)}")
            await asyncio.sleep(5)

# Example usage
async def main():
    try:
        redis_client = await asyncio.wait_for(connect_redis(), timeout=60)
        # Use redis_client here
    except CustomTimeoutError:
        logger.error("Timed out while trying to connect to Redis")
    finally:
        if 'redis_client' in locals() and redis_client is not None:
            redis_client.close()
            await redis_client.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())