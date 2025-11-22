from django.core.cache import cache
from django.db.models import QuerySet
import json
from hashlib import md5


def _serialize_value(value):
    """Serialize database or python objects for consistent caching."""
    
    if isinstance(value, QuerySet):
        return list(value.values())
    
    if isinstance(value, (dict, list, str, int, float, bool, type(None))):
        return value

    try:
        from django.forms.models import model_to_dict
        return model_to_dict(value)
    except Exception:
        pass

    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return str(value)


def _normalize_key(key):
    """Ensure cache keys are safe and unique."""
    if len(key) > 200:
        return md5(key.encode("utf-8")).hexdigest()
    return key


def cache_get_or_set(key: str, value_func, timeout: int = None):
    """
    Reusable safe caching.

    Usage:
        def fetch_data():
            return Course.objects.all()

        data = cache_get_or_set("courses:all", fetch_data, 60)

    Args:
        key (str): cache key
        value_func (callable): function that returns the actual value if cache is empty
        timeout (int, optional): cache lifetime in seconds

    Returns:
        Any: cached or freshly computed value
    """

    key = _normalize_key(key)

    cached_value = cache.get(key)
    if cached_value is not None:
        return cached_value

    value = value_func()
    serialized = _serialize_value(value)
    cache.set(key, serialized, timeout=timeout)

    return serialized
