import os
from redis import Redis
from rq import Worker, Queue, Connection

# Render will automatically provide this from the Environment Variables you set earlier!
redis_url = os.getenv('REDIS_URL')

if not redis_url:
    raise ValueError("REDIS_URL is not set! Please add it to Render.")

redis_conn = Redis.from_url(redis_url)

if __name__ == '__main__':
    print("👷 Python Worker is booting up and listening to Upstash Redis...")
    with Connection(redis_conn):
        # Listen to the exact same queue we will send videos to
        worker = Worker(['video-processing'])
        worker.work()