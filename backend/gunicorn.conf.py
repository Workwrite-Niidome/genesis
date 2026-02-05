# GENESIS v3 — Gunicorn Configuration for Production
# https://docs.gunicorn.org/en/stable/settings.html

import multiprocessing
import os

# ---------------------------------------------------------------------------
# Server socket
# ---------------------------------------------------------------------------
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------
# Default: 4 workers, or calculate from CPU count (2 * cores + 1)
_default_workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
workers = int(os.getenv("GUNICORN_WORKERS", _default_workers))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 5000
max_requests_jitter = 500

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
timeout = 120
graceful_timeout = 30
keepalive = 5

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Log to stdout/stderr for Docker log collection
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "warning").lower()

# Structured access log format (compatible with JSON log aggregation)
access_log_format = (
    '{"remote_addr":"%(h)s",'
    '"request_method":"%(m)s",'
    '"request_path":"%(U)s",'
    '"query_string":"%(q)s",'
    '"status":"%(s)s",'
    '"response_length":"%(B)s",'
    '"request_time":"%(D)s",'
    '"user_agent":"%(a)s",'
    '"referer":"%(f)s"}'
)

# ---------------------------------------------------------------------------
# Process naming
# ---------------------------------------------------------------------------
proc_name = "genesis-backend"

# ---------------------------------------------------------------------------
# Server mechanics
# ---------------------------------------------------------------------------
# Preload application for faster worker startup and shared memory
preload_app = True

# Restart workers gracefully on SIGHUP
reload = False

# Temporary file directory for worker heartbeat
tmp_upload_dir = None

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
# Limit request line size (default 8190)
limit_request_line = 8190
# Limit request header fields
limit_request_fields = 100
# Limit request header field size
limit_request_field_size = 8190

# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------
def on_starting(server):
    """Called just before the master process is initialized."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Spawning workers")


def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    worker.log.info("worker received INT or QUIT signal")


def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal (timeout)."""
    worker.log.info("worker received SIGABRT signal")
