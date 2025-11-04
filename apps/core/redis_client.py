import redis
from django.conf import settings

# Use REDIS_URL from settings or fallback to localhost
REDIS_URL = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")
r = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)