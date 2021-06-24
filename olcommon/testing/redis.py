# -*- coding:utf-8 -*-

from plone.testing import Layer
import redis
import redis.exceptions

import time
import os
import os.path
import shutil
import subprocess
import tempfile


REDIS_CONFIGURATION_TEMPLATE = """
bind 127.0.0.1
port 0
unixsocket {self[redis_socket]}
unixsocketperm 700
timeout 0
tcp-keepalive 300
loglevel warning
logfile ""
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir {self[redis_dir]}
"""

class RedisLayer(Layer):
    """Layer for creating a redis instance"""

    def setUp(self):
        self['redis_dir'] = tempfile.mkdtemp()
        self['redis_configuration_file'] = os.path.join(self['redis_dir'], 'config')
        self['redis_socket'] = os.path.join(self['redis_dir'], 'socket')
        self['redis_url'] = f'unix://{self["redis_socket"]}'
        with open(self["redis_configuration_file"], "w") as fout:
            fout.write(REDIS_CONFIGURATION_TEMPLATE.format(self=self))
        self['redis_process'] = None

    def startRedis(self):
        self["redis_process"] = subprocess.Popen(
            (
                f'{os.environ["REDIS_PREFIX"]}/src/redis-server',
                self["redis_configuration_file"],
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        tries = 0
        while True:
            tries += 1
            try:
                redis_instance = redis.StrictRedis.from_url(self["redis_url"], decode_responses=True)
                info = redis_instance.info()
                redis_instance.set('testing:set', 'foo')
                break
            except redis.exceptions.ConnectionError as e:
                if tries >= 10:
                    raise Exception("Could not connect to redis") from e
                time.sleep(0.4)

    def stopRedis(self):
        # stop redis
        process = self["redis_process"]
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if self.poll() is None:
                process.kill()
                process.wait(timeout=10)

        # remove redis database
        try:
            os.remove(os.path.join(self['redis_dir'], 'dump.rdb'))
        except FileNotFoundError:
            pass

    def testSetUp(self):
        if self['redis_process'] is not None:
            self.stopRedis()
            self['redis_process'] = None
        self.startRedis()

    def testTearDown(self):
        self.stopRedis()

    def tearDown(self):
        self.stopRedis()
        shutil.rmtree(self["redis_dir"])


REDIS_LAYER = RedisLayer()
