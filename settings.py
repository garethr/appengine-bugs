import os

DEBUG = os.environ['SERVER_SOFTWARE'].startswith('Dev')

# enable or disable the memcache here, useful for debugging
CACHE = not os.environ['SERVER_SOFTWARE'].startswith('Dev')

# URL of the current system, used in feeds
SYSTEM_URL = "http://gitbug.appspot.com"