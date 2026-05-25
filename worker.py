import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from redis import Redis
from rq import Worker, Queue, Connection

# --- THE FREE TIER HACK ---
# Render requires a "Web Service" to use a port. This creates a fake, invisible website.
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Worker is alive and listening!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

# Start the fake web server in the background
threading.Thread(target=run_dummy_server, daemon=True).start()
# --------------------------

# --- YOUR ACTUAL WORKER ---
redis_url = os.getenv('REDIS_URL')

if not redis_url:
    raise ValueError("REDIS_URL is not set! Please add it to Render.")

redis_conn = Redis.from_url(redis_url)

if __name__ == '__main__':
    print("👷 Python Worker is booting up (Free Tier Mode)...")
    with Connection(redis_conn):
        worker = Worker(['video-processing'])
        worker.work()