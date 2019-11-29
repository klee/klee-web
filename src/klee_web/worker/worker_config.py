import os
import redis


class WorkerConfig():
    """
    Change the settings for the redis queue within the 'klee_worker' namespace.
    """
    NAMESPACE = 'klee_worker'
    MEMORY_UNIT = 'm'

    def __init__(self):
        self.r = redis.StrictRedis(host=os.environ['REDIS_HOST'],
                                   port=os.environ['REDIS_PORT'])

    @property
    def cpu_share(self):
        return self.get_config('cpu_share', default=100)

    @property
    def memory_limit(self):
        return self.get_config('memory_limit', default=1024)

    @property
    def timeout(self):
        return self.get_config('timeout', default=30)

    @property
    def container_timeout(self):
        return self.get_config('container_timeout', default=600)

    def get_config(self, key, default=None):
        value = self.r.get('{}:{}'.format(WorkerConfig.NAMESPACE, key))
        if value is not None and value.isdigit():
            return int(value)
        else:
            return value or default

    def set_config(self, key, value):
        self.r.set('{}:{}'.format(WorkerConfig.NAMESPACE, key), value)
