import os

# when running the tests we don't have the environment variable available
try:
    debug = os.environ['SERVER_SOFTWARE'].startswith('Dev')
except KeyError:
    debug = False

DEBUG = debug

# enable or disable the memcache here, useful for debugging
CACHE = not debug

# URL of the current system, used in feeds
SYSTEM_URL = "http://gitbug.appspot.com"