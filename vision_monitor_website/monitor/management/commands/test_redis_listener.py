import redis
import time

REDIS_HOST = '192.168.0.71'
REDIS_PORT = 6379
REDIS_MESSAGE_CHANNEL = 'llm_messages'
REDIS_STATE_RESULT_CHANNEL = 'state_result'

def listen_to_redis():
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    pubsub = redis_client.pubsub()
    pubsub.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)

    print(f"Subscribed to Redis channels: {REDIS_MESSAGE_CHANNEL}, {REDIS_STATE_RESULT_CHANNEL}")

    try:
        for message in pubsub.listen():
            print(f"Received from pubsub: {message}")
            
            if message['type'] == 'message':
                channel = message['channel'].decode('utf-8')
                data = message['data']
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                print(f"Received message from Redis channel {channel}: {data}")

    except KeyboardInterrupt:
        print("Listener stopped")
    finally:
        pubsub.unsubscribe()
        redis_client.close()
        print("Redis connection closed")

if __name__ == "__main__":
    listen_to_redis()