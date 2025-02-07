import logging
from typing import Generator

import orjson
from pymemcache.client.base import PooledClient
from pymemcache.exceptions import MemcacheError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheSerde:
    def serialize(self, key, value):
        if isinstance(value, str):
            return value, 1
        return orjson.dumps(value), 2

    def deserialize(self, key, value, flags):
        if flags == 1:
            return value
        if flags == 2:
            return orjson.loads(value)
        raise Exception("Unknown serialization format")


def generateClient() -> Generator[PooledClient, None, None]:
    try:
        yield PooledClient(
            ("127.0.0.1", 11211),
            max_pool_size=16,
            # serde=CacheSerde(),
            # connect_timeout=...,
            # timeout=...,
        )
    except MemcacheError as e:
        logger.error(e)
    finally:
        # TODO: Shutdown tasks here
        return
