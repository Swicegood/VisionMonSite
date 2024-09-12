import asyncio
import aioredis
import logging
from .config import REDIS_HOST, REDIS_PORT
logger = logging.getLogger(__name__)

async def connect_redis():
    while True:
        try:
            redis_client = await aioredis.create_redis_pool(f'redis://{REDIS_HOST}:{REDIS_PORT}')
            logger.info("Connected to Redis")
            return redis_client
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            await asyncio.sleep(5)