# Gunicorn configuration file for Render Free Tier (512MB RAM)
import multiprocessing

# Bind to the PORT environment variable (Render requirement)
bind = "0.0.0.0:10000"

# Worker processes - CRITICAL for memory management
# Use only 1 worker for free tier to avoid OOM
workers = 1

# Worker class - use sync for lower memory usage
worker_class = "sync"

# Threads per worker - helps handle concurrent requests
threads = 2

# Worker timeout (30 seconds)
timeout = 30

# Maximum requests a worker will process before restarting
# This helps prevent memory leaks
max_requests = 100
max_requests_jitter = 10

# Preload app to save memory (shared code between workers)
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Graceful timeout
graceful_timeout = 30

# Keep alive
keepalive = 2
