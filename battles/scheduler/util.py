import os
import json
from pymemcache.client.base import Client

def json_serializer(key, value):
    if type(value) == str:
        return value, 1
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
