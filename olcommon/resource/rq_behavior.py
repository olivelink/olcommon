from ctq import acquire
from functools import lru_cache
from uuid import UUID
from hashlib import md5

import rq
import math


class RqBehavior:

    @lru_cache
    def get_queue(self, name):
        return rq.Queue(name, connection=acquire().redis)

    @lru_cache(1000)
    def get_write_group_queue(self, key):

        # Cast our key to md5 hashable bytes
        if isinstance(key, UUID):
            key = key.bytes
        elif isinstance(key, str):
            key = key.encode('utf-8')
        else:
            raise NotImplementedError(f"Not implemented for key of type {type(key)}")

        # Calculate a hash of key that is a float between 0.0 and 1.0
        key_hash = md5(self.account_id.bytes).digest()
        key_hash = key_hash[0]
        key_hash = key_hash / 256

        # Convert the key_hash to a group name
        write_groups = acquire().registry["rq_write_group_queues"]
        index = int(math.floor(key_hash * len(write_groups)))
        group_name = write_groups[index]

        return self.get_queue(group_name)
