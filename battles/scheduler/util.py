import os
import json
from itertools import chain
from functools import wraps
from time import perf_counter


from pymemcache.client.base import Client

MEMCACHE_LIFETIME = 10


def json_serializer(key, value):
    if type(value) == str:
        return value, 1
    elif type(value).__name__ == 'WGAPI':
        return json.dumps(value.data), 2
    return json.dumps(value), 2


def json_deserializer(key, value, flags):
    if flags == 1:
        return value
    if flags == 2:
        return json.loads(value)
    raise Exception("Unknown serialization format")


memcache = Client(
    (os.environ.get('MEMCACHE_HOSTNAME', 'localhost'), 11211),
    serializer=json_serializer,
    deserializer=json_deserializer
)


def log_time(func):
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        end = perf_counter()
        print(f'{func.__name__} used {end-start} seconds')
        return result
    return wrapper


def memcached(timeout=MEMCACHE_LIFETIME, list_field=None):
    def memcache_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = '%s/%s' % (func.__name__, '/'.join([i for i in chain(
                [repr(i) for i in args],
                [f'{k}={v}' for k, v in kwargs.items() if k != list_field]
            )]))
            print(key)
            if list_field:
                keys = {
                    f'{key}/{sub_key}': sub_key
                    for sub_key in kwargs[list_field]
                }
                data = memcache.get_many(keys)
                missed_keys = keys.keys() - data.keys()
                data = {keys[k]: v for k, v in data.items()}
                if missed_keys:
                    print(missed_keys)
                    kwargs[list_field] = list(keys[i] for i in missed_keys)
                    new_data = func(*args, **kwargs)
                    memcache.set_many({f'{key}/{k}': v for k, v in new_data.items()},
                                      expire=timeout)
                    data.update(new_data)
                return data
            else:
                data = memcache.get(key)
                if data:
                    return data
                data = func(*args, **kwargs)
                memcache.set(key, value=data, expire=timeout)
                return data
        return wrapper
    return memcache_decorator
