import multiprocessing

'''
Config file for gunicorn

Start command
gunicorn run:app -c guniconf.py -D
'''

# Server Socket
bind = 'unix:/var/run/gunicorn/gunicorn_spam.sock'
backlog = 2048

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
max_requests = 0
timeout = 30
keepalive = 2
debug = False
spew = False

# Logging
accesslog = None
errorlog = '/var/www/spam_api/logs/gunicorn-error.log'
loglevel = 'info'
logconfig = None

# Process Name
proc_name = 'spam_api'
