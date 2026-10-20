import os

bind = '0.0.0.0:8000'
workers = int(os.getenv('WEB_WORKERS', '2'))
worker_class = 'gthread'
threads = int(os.getenv('WEB_THREADS', '4'))
timeout = 120
graceful_timeout = 120
accesslog = None  # Signed document URLs must not appear in access logs.
errorlog = '-'
capture_output = True
control_socket_disable = True  # Lifecycle management is handled by Docker Compose.
forwarded_allow_ips = '*'  # The backend port is reachable only inside Compose.
